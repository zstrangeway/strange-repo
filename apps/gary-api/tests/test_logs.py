"""What the Gherkin specs cannot reach.

features/logging.feature drives the real app and reads the real log, which
is where the behaviour is pinned down. This file covers the corners a
request cannot get to: the human-readable format, a scope that is not a
request, and a request that blows up before it can answer.
"""

import asyncio
import io
import json
import logging
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from gary_api import logs


class LogTestCase(unittest.TestCase):
    """Configures logging into a buffer and puts it back afterwards."""

    format = "json"

    def setUp(self):
        self.stream = io.StringIO()
        root = logging.getLogger()
        self.previous = (root.handlers, root.level)
        with patch.dict("os.environ", {"LOG_FORMAT": self.format}):
            logs.configure(stream=self.stream)

    def tearDown(self):
        # The level as well as the handlers: one test here drops the root to
        # DEBUG, and leaving it there makes every later test noisier.
        root = logging.getLogger()
        root.handlers, root.level = self.previous

    @property
    def written(self):
        return self.stream.getvalue()

    @property
    def objects(self):
        return [json.loads(line) for line in self.written.splitlines() if line.strip()]


class JsonTests(LogTestCase):
    def test_every_level_reaches_the_log(self):
        logger = logs.get_logger("gary_api.tests")
        logging.getLogger().setLevel(logging.DEBUG)

        logger.debug("a")
        logger.info("b")
        logger.warning("c")
        logger.error("d")
        logger.critical("e")

        self.assertEqual(
            [(line["message"], line["level"]) for line in self.objects],
            [
                ("a", "debug"),
                ("b", "info"),
                ("c", "warning"),
                ("d", "error"),
                ("e", "critical"),
            ],
        )

    def test_a_field_named_after_a_record_attribute_does_not_raise(self):
        # `name`, `module`, `args` and a dozen others make makeRecord throw.
        # Losing the call over the choice of a field name would be a poor
        # trade, so they are renamed the way the reserved ones are.
        logs.get_logger("gary_api.tests").info("saved", name="ada", module="signup")

        line = self.objects[0]
        self.assertEqual(line["name_"], "ada")
        self.assertEqual(line["module_"], "signup")
        self.assertEqual(line["logger"], "gary_api.tests")

    def test_a_field_set_through_plain_extra_is_picked_up(self):
        # Code that knows nothing about this module still gets its fields on
        # the line, which is what makes the same formatter work for uvicorn.
        logging.getLogger("gary_api.tests").info("done", extra={"rows": 3})

        self.assertEqual(self.objects[0]["rows"], 3)


class ContextTests(LogTestCase):
    def test_bound_fields_are_readable_and_then_gone(self):
        self.assertEqual(logs.context(), {})

        with logs.bind(request_id="abc", tenant="gary"):
            self.assertEqual(logs.context(), {"request_id": "abc", "tenant": "gary"})

        self.assertEqual(logs.context(), {})

    def test_bindings_nest(self):
        with logs.bind(request_id="abc"):
            with logs.bind(step="two"):
                logs.get_logger("gary_api.tests").info("inner")
            logs.get_logger("gary_api.tests").info("outer")

        inner, outer = self.objects
        self.assertEqual((inner["request_id"], inner["step"]), ("abc", "two"))
        self.assertNotIn("step", outer)

    def test_a_bound_field_cannot_overwrite_a_standard_one(self):
        with logs.bind(level="urgent"):
            logs.get_logger("gary_api.tests").info("odd")

        line = self.objects[0]
        self.assertEqual(line["level"], "info")
        self.assertEqual(line["level_"], "urgent")


class TextFormatTests(LogTestCase):
    """LOG_FORMAT=text. For eyes, not for shippers.

    It exists because the console mail provider logs a whole reset email,
    and JSON escaping turns that into one unreadable line at exactly the
    moment a developer needs to read it.
    """

    format = "text"

    def test_a_plain_line_carries_the_essentials(self):
        logs.get_logger("gary_api.tests").info("mail.logged")

        line = self.written.strip()
        self.assertRegex(line, r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z info    gary_api.tests mail.logged$")

    def test_fields_follow_the_message(self):
        logs.get_logger("gary_api.tests").info("mail.logged", to="ada@example.com")

        self.assertIn("to='ada@example.com'", self.written)

    def test_a_failure_puts_the_stack_underneath(self):
        try:
            raise ValueError("no such account")
        except ValueError:
            logs.get_logger("gary_api.tests").exception("work.failed")

        first, *rest = self.written.splitlines()
        self.assertIn("work.failed", first)
        self.assertIn("ValueError: no such account", "\n".join(rest))


class RequestContextTests(LogTestCase):
    def test_a_scope_that_is_not_a_request_passes_straight_through(self):
        # Lifespan and websockets have no response to hang a header off, and
        # no method or path to summarise.
        seen = []

        async def app(scope, receive, send):
            seen.append(scope["type"])

        asyncio.run(logs.RequestContext(app)({"type": "lifespan"}, None, None))

        self.assertEqual(seen, ["lifespan"])
        self.assertEqual(self.objects, [])

    def test_a_request_that_raises_is_logged_with_its_id(self):
        async def app(scope, receive, send):
            raise RuntimeError("it fell over")

        client = TestClient(logs.RequestContext(app))
        with self.assertRaises(RuntimeError):
            client.get("/boom")

        line = self.objects[0]
        self.assertEqual(line["message"], "http.request")
        self.assertEqual(line["status"], 500)
        self.assertEqual(line["path"], "/boom")
        self.assertEqual(line["error"]["type"], "RuntimeError")
        # The point of logging it here rather than letting it escape: outside
        # the bound block the id is gone and the 500 is an orphan.
        self.assertTrue(line["request_id"])
