"""The provider interface, the stub, and the Anthropic call itself.

Nothing here reaches the network. The Anthropic client is replaced, because
the specs cannot cover this module at all — a suite that called a real model
would be slow, cost somebody money, and test nothing repeatable.
"""

import os
import unittest
import unittest.mock

import anthropic
import httpx2
from support import InAScratchHome

from scout import providers
from scout.errors import ScoutError
from scout.providers.anthropic_api import DEFAULT_MODEL, AnthropicProvider


def _response(text, stop_reason="end_turn"):
    block = unittest.mock.Mock(type="text", text=text)
    return unittest.mock.Mock(content=[block], stop_reason=stop_reason)


def _client(response=None, error=None):
    client = unittest.mock.Mock()
    client.messages.create.side_effect = error
    if error is None:
        client.messages.create.return_value = response
    return unittest.mock.patch(
        "scout.providers.anthropic_api.anthropic.Anthropic", return_value=client
    ), client


class Loading(unittest.TestCase):
    def test_the_default_is_anthropic(self):
        self.assertEqual(providers.load().name, "anthropic")

    def test_the_stub_can_be_asked_for_by_name(self):
        self.assertEqual(providers.load("fake").name, "fake")

    def test_a_provider_that_does_not_exist_says_which_ones_do(self):
        with self.assertRaises(ScoutError) as caught:
            providers.load("ollama")
        self.assertIn("anthropic", caught.exception.detail)


class TheStub(InAScratchHome):
    def test_it_returns_the_master_when_nothing_was_asked_for(self):
        # So a scenario that does not care what the model said does not have
        # to invent a draft.
        self.assertEqual(
            providers.load("fake").tailor(master="# Ada\n", posting="x"), "# Ada\n"
        )


class TheAnthropicProvider(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-not-real"
        self.addCleanup(self._restore)

    def _restore(self):
        if self.previous is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = self.previous

    def test_the_default_model_is_sonnet(self):
        self.assertEqual(AnthropicProvider().model, DEFAULT_MODEL)

    def test_the_model_can_be_set_from_the_environment(self):
        with unittest.mock.patch.dict(os.environ, {"SCOUT_MODEL": "claude-opus-5"}):
            self.assertEqual(AnthropicProvider().model, "claude-opus-5")

    def test_a_missing_key_is_caught_before_a_connection_is_opened(self):
        os.environ.pop("ANTHROPIC_API_KEY")
        with (
            unittest.mock.patch(
                "scout.providers.anthropic_api.anthropic.Anthropic"
            ) as client,
            self.assertRaises(ScoutError) as caught,
        ):
            AnthropicProvider().tailor(master="# Ada\n", posting="x")
        client.assert_not_called()
        self.assertIn("ANTHROPIC_API_KEY", str(caught.exception))

    def test_it_returns_the_text_the_model_sent(self):
        patched, client = _client(_response("# Ada\n\ntailored\n"))
        with patched:
            draft = AnthropicProvider().tailor(master="# Ada\n", posting="a posting")
        # Stripped: a trailing newline from the model is not content.
        self.assertEqual(draft, "# Ada\n\ntailored")
        sent = client.messages.create.call_args.kwargs
        self.assertEqual(sent["model"], DEFAULT_MODEL)
        self.assertIn("may not add anything", sent["system"].lower().replace("\n", " "))
        self.assertIn("a posting", sent["messages"][0]["content"])

    def test_a_refusal_is_a_failure_rather_than_an_empty_resume(self):
        patched, _ = _client(_response("", stop_reason="refusal"))
        with patched, self.assertRaises(ScoutError) as caught:
            AnthropicProvider().tailor(master="# Ada\n", posting="x")
        self.assertIn("declined", str(caught.exception))

    def test_an_empty_response_is_a_failure(self):
        patched, _ = _client(_response("   "))
        with patched, self.assertRaises(ScoutError) as caught:
            AnthropicProvider().tailor(master="# Ada\n", posting="x")
        self.assertIn("returned nothing", str(caught.exception))

    def test_an_http_error_says_what_came_back(self):
        request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
        error = anthropic.APIStatusError(
            "overloaded", response=httpx2.Response(529, request=request), body=None
        )
        patched, _ = _client(error=error)
        with patched, self.assertRaises(ScoutError) as caught:
            AnthropicProvider().tailor(master="# Ada\n", posting="x")
        self.assertIn("529", str(caught.exception))

    def test_a_connection_error_is_not_a_traceback(self):
        error = anthropic.APIConnectionError(
            message="no route to host",
            request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"),
        )
        patched, _ = _client(error=error)
        with patched, self.assertRaises(ScoutError) as caught:
            AnthropicProvider().tailor(master="# Ada\n", posting="x")
        self.assertIn("model call failed", str(caught.exception))
