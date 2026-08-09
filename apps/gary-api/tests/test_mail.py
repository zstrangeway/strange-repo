import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import AsyncMock, patch

import httpx

from gary_api import mail
from gary_api.mail import DEFAULT_SENDER, MailError, Message, mailer, sender
from gary_api.mail.console import ConsoleMailer
from gary_api.mail.resend import API_URL, ResendMailer


class MailTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # mailer() caches its answer, which is the point in a running app and
        # a nuisance across tests that each configure it differently.
        mailer.cache_clear()
        self.addCleanup(mailer.cache_clear)


class SenderTests(MailTestCase):
    def test_falls_back_to_the_resend_test_address(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(sender(), DEFAULT_SENDER)

    def test_uses_mail_from_when_set(self):
        with patch.dict("os.environ", {"MAIL_FROM": "gary <no-reply@gary.test>"}):
            self.assertEqual(sender(), "gary <no-reply@gary.test>")


class ProviderSelectionTests(MailTestCase):
    def test_defaults_to_the_console(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsInstance(mailer(), ConsoleMailer)

    def test_mail_provider_chooses(self):
        with patch.dict("os.environ", {"MAIL_PROVIDER": "resend", "RESEND_API_KEY": "k"}):
            self.assertIsInstance(mailer(), ResendMailer)

    def test_a_resend_key_on_its_own_implies_resend(self):
        with patch.dict("os.environ", {"RESEND_API_KEY": "k"}, clear=True):
            self.assertIsInstance(mailer(), ResendMailer)

    def test_mail_provider_wins_over_an_idle_resend_key(self):
        with patch.dict(
            "os.environ", {"MAIL_PROVIDER": "console", "RESEND_API_KEY": "k"}
        ):
            self.assertIsInstance(mailer(), ConsoleMailer)

    def test_rejects_a_provider_it_does_not_have(self):
        with patch.dict("os.environ", {"MAIL_PROVIDER": "carrier-pigeon"}, clear=True):
            with self.assertRaises(MailError) as caught:
                mailer()

        self.assertIn("carrier-pigeon", str(caught.exception))
        # Name the way out, not just the problem.
        self.assertIn("resend", str(caught.exception))

    def test_resend_without_a_key_says_which_key(self):
        with patch.dict("os.environ", {"MAIL_PROVIDER": "resend"}, clear=True):
            with self.assertRaises(MailError) as caught:
                mailer()

        self.assertIn("RESEND_API_KEY", str(caught.exception))

    def test_resend_is_built_with_the_configured_sender(self):
        with patch.dict(
            "os.environ",
            {"RESEND_API_KEY": "k", "MAIL_FROM": "gary <no-reply@gary.test>"},
            clear=True,
        ):
            built = mailer()

        self.assertEqual(built._sender, "gary <no-reply@gary.test>")

    def test_resend_points_at_the_real_api_by_default(self):
        with patch.dict("os.environ", {"RESEND_API_KEY": "k"}, clear=True):
            self.assertEqual(mailer()._api_url, API_URL)

    def test_resend_api_url_can_be_redirected(self):
        with patch.dict(
            "os.environ",
            {"RESEND_API_KEY": "k", "RESEND_API_URL": "http://127.0.0.1:9/emails"},
            clear=True,
        ):
            self.assertEqual(mailer()._api_url, "http://127.0.0.1:9/emails")

    def test_resolves_once_and_reuses(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIs(mailer(), mailer())


class ReportConfigurationTests(MailTestCase):
    def test_reports_the_provider_and_the_sender(self):
        with patch.dict("os.environ", {"MAIL_FROM": "gary <no-reply@gary.test>"}, clear=True):
            with self.assertLogs("gary_api.mail", level="INFO") as captured:
                mail.report_configuration()

        # The fields, not the rendered text: the message is now a stable event
        # name and the answer to "which provider" lives beside it.
        record = captured.records[0]
        self.assertEqual(record.msg, "mail.configured")
        self.assertEqual(record.provider, "console")
        self.assertEqual(record.sender, "gary <no-reply@gary.test>")

    def test_reports_a_broken_config_without_raising(self):
        with patch.dict("os.environ", {"MAIL_PROVIDER": "resend"}, clear=True):
            with self.assertLogs("gary_api.mail", level="ERROR") as captured:
                mail.report_configuration()

        record = captured.records[0]
        self.assertEqual(record.msg, "mail.misconfigured")
        self.assertIn("RESEND_API_KEY", record.reason)


class ConsoleMailerTests(MailTestCase):
    async def test_logs_the_message_in_full(self):
        message = Message(
            to="ada@example.com",
            subject="Reset your password",
            text="Follow https://gary.test/reset?token=abc123",
        )

        with self.assertLogs("gary_api.mail.console", level="INFO") as captured:
            await ConsoleMailer().send(message)

        record = captured.records[0]
        self.assertEqual(record.to, "ada@example.com")
        self.assertEqual(record.subject, "Reset your password")
        # The link is the entire value of the console provider.
        self.assertIn("token=abc123", record.body)


class ResendMailerTests(MailTestCase):
    def setUp(self):
        super().setUp()
        self.message = Message(
            to="ada@example.com", subject="Reset your password", text="Follow the link"
        )
        self.mailer = ResendMailer(api_key="a-key", sender="gary <no-reply@gary.test>")

    def _client(self, post):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post = post
        return patch("httpx.AsyncClient", return_value=client)

    async def test_posts_the_message_to_resend(self):
        post = AsyncMock(return_value=httpx.Response(200, json={"id": "1"}))

        with self._client(post):
            await self.mailer.send(self.message)

        url, = post.call_args.args
        self.assertEqual(url, API_URL)
        self.assertEqual(
            post.call_args.kwargs["headers"], {"authorization": "Bearer a-key"}
        )
        self.assertEqual(
            post.call_args.kwargs["json"],
            {
                "from": "gary <no-reply@gary.test>",
                "to": ["ada@example.com"],
                "subject": "Reset your password",
                "text": "Follow the link",
            },
        )

    async def test_raises_with_the_body_when_resend_refuses(self):
        post = AsyncMock(
            return_value=httpx.Response(403, text="The gary.test domain is not verified")
        )

        with self._client(post):
            with self.assertRaises(MailError) as caught:
                await self.mailer.send(self.message)

        # The status alone cannot tell an unverified domain from a dead key.
        self.assertIn("403", str(caught.exception))
        self.assertIn("not verified", str(caught.exception))

    async def test_raises_when_resend_cannot_be_reached(self):
        post = AsyncMock(side_effect=httpx.ConnectError("no route to host"))

        with self._client(post):
            with self.assertRaises(MailError) as caught:
                await self.mailer.send(self.message)

        self.assertIn("no route to host", str(caught.exception))


class ResendOverTheWireTests(MailTestCase):
    """The same adapter against a real socket rather than a mock.

    A mocked client agrees with whatever resend.py happens to send, so it
    cannot catch a malformed header or a body that never gets serialised.
    This runs the actual httpx request against a local server and asserts on
    what arrived. It still cannot prove Resend accepts it — that needs the
    live API, which this environment's egress policy blocks.
    """

    def setUp(self):
        super().setUp()
        received = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["content-length"])
                received["path"] = self.path
                # Lowercased: the wire is case-insensitive but a plain dict
                # is not, and httpx capitalises Content-Type.
                received["headers"] = {
                    name.lower(): value for name, value in self.headers.items()
                }
                received["body"] = json.loads(self.rfile.read(length))
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"id": "sent"}')

            def log_message(self, *args):
                pass

        self.received = received
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        # Cleanups run last-registered-first, so these read bottom-up:
        # shutdown, then close the socket, then join. Joining a server still
        # in serve_forever never returns.
        self.addCleanup(thread.join)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

        host, port = self.server.server_address
        self.api_url = f"http://{host}:{port}/emails"

    async def test_sends_a_request_resend_would_recognise(self):
        mailer_ = ResendMailer(
            api_key="a-key", sender="gary <no-reply@gary.test>", api_url=self.api_url
        )

        await mailer_.send(
            Message(
                to="ada@example.com",
                subject="Reset your password",
                text="Follow https://gary.test/reset?token=abc123",
            )
        )

        self.assertEqual(self.received["path"], "/emails")
        self.assertEqual(self.received["headers"]["authorization"], "Bearer a-key")
        self.assertEqual(
            self.received["headers"]["content-type"], "application/json"
        )
        self.assertEqual(
            self.received["body"],
            {
                "from": "gary <no-reply@gary.test>",
                "to": ["ada@example.com"],
                "subject": "Reset your password",
                "text": "Follow https://gary.test/reset?token=abc123",
            },
        )


class SendTests(MailTestCase):
    async def test_hands_the_message_to_the_configured_provider(self):
        provider = AsyncMock()
        message = Message(to="ada@example.com", subject="Hello", text="Hello")

        with patch.object(mail, "mailer", return_value=provider):
            await mail.send(message)

        provider.send.assert_awaited_once_with(message)


if __name__ == "__main__":
    unittest.main()
