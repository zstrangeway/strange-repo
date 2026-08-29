"""The provider interface, the stub, and both real clients.

Nothing here reaches the network. Both clients are replaced, because the specs
cannot cover these modules at all — a suite that called a real model would be
slow, cost somebody money, and test nothing repeatable. `scout-smoke` is what
calls one on purpose.
"""

import os
import unittest
import unittest.mock

import anthropic
import httpx2
import openai
from support import InAScratchHome

from scout import providers
from scout.errors import ScoutError
from scout.providers.anthropic_api import DEFAULT_MODEL, AnthropicProvider
from scout.providers.openrouter import OpenRouterProvider
from scout.providers.prompt import SYSTEM


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

    def test_openrouter_can_be_asked_for_by_name(self):
        self.assertEqual(providers.load("openrouter").name, "openrouter")

    def test_a_provider_that_does_not_exist_says_which_ones_do(self):
        with self.assertRaises(ScoutError) as caught:
            providers.load("ollama")
        self.assertIn("anthropic", caught.exception.detail)
        self.assertIn("openrouter", caught.exception.detail)


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


class TheOpenRouterProvider(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("OPENROUTER_API_KEY")
        os.environ["OPENROUTER_API_KEY"] = "sk-or-not-real"
        self.addCleanup(self._restore)

    def _restore(self):
        if self.previous is None:
            os.environ.pop("OPENROUTER_API_KEY", None)
        else:
            os.environ["OPENROUTER_API_KEY"] = self.previous

    def _client(self, choices=None, error=None):
        client = unittest.mock.Mock()
        client.chat.completions.create.side_effect = error
        if error is None:
            client.chat.completions.create.return_value = unittest.mock.Mock(
                choices=choices
            )
        return unittest.mock.patch(
            "scout.providers.openrouter.openai.OpenAI", return_value=client
        ), client

    @staticmethod
    def _choice(content):
        return [unittest.mock.Mock(message=unittest.mock.Mock(content=content))]

    def test_the_default_model_is_sonnet_in_openrouter_s_namespace(self):
        self.assertEqual(OpenRouterProvider().model, "anthropic/claude-sonnet-5")

    def test_a_missing_key_is_caught_before_a_connection_is_opened(self):
        os.environ.pop("OPENROUTER_API_KEY")
        with (
            unittest.mock.patch("scout.providers.openrouter.openai.OpenAI") as client,
            self.assertRaises(ScoutError) as caught,
        ):
            OpenRouterProvider().tailor(master="# Ada\n", posting="x")
        client.assert_not_called()
        self.assertIn("OPENROUTER_API_KEY", str(caught.exception))

    def test_it_sends_the_same_instruction_the_anthropic_provider_does(self):
        # The two drifting apart is the failure nobody notices, so the prompt
        # lives in one module and this asserts both actually use it.
        patched, client = self._client(self._choice("# Ada\n\ntailored"))
        with patched:
            draft = OpenRouterProvider().tailor(master="# Ada\n", posting="a posting")
        self.assertEqual(draft, "# Ada\n\ntailored")
        sent = client.chat.completions.create.call_args.kwargs
        self.assertEqual(sent["messages"][0]["content"], SYSTEM)
        self.assertIn("a posting", sent["messages"][1]["content"])

    def test_it_points_at_openrouter_rather_than_openai(self):
        patched, _ = self._client(self._choice("# Ada"))
        with (
            patched,
            unittest.mock.patch(
                "scout.providers.openrouter.openai.OpenAI"
            ) as constructed,
        ):
            constructed.return_value.chat.completions.create.return_value = (
                unittest.mock.Mock(choices=self._choice("# Ada"))
            )
            OpenRouterProvider().tailor(master="# Ada\n", posting="x")
        self.assertEqual(
            constructed.call_args.kwargs["base_url"], "https://openrouter.ai/api/v1"
        )

    def test_a_downstream_provider_being_down_arrives_as_no_choices(self):
        patched, _ = self._client(choices=[])
        with patched, self.assertRaises(ScoutError) as caught:
            OpenRouterProvider().tailor(master="# Ada\n", posting="x")
        self.assertIn("no choices", str(caught.exception))

    def test_an_empty_message_is_a_failure(self):
        patched, _ = self._client(self._choice(None))
        with patched, self.assertRaises(ScoutError) as caught:
            OpenRouterProvider().tailor(master="# Ada\n", posting="x")
        self.assertIn("returned nothing", str(caught.exception))

    def test_an_http_error_says_what_came_back(self):
        error = openai.APIStatusError(
            "rate limited",
            response=httpx2.Response(
                429, request=httpx2.Request("POST", "https://openrouter.ai/api/v1")
            ),
            body=None,
        )
        patched, _ = self._client(error=error)
        with patched, self.assertRaises(ScoutError) as caught:
            OpenRouterProvider().tailor(master="# Ada\n", posting="x")
        self.assertIn("429", str(caught.exception))

    def test_a_connection_error_is_not_a_traceback(self):
        error = openai.APIConnectionError(
            request=httpx2.Request("POST", "https://openrouter.ai/api/v1")
        )
        patched, _ = self._client(error=error)
        with patched, self.assertRaises(ScoutError) as caught:
            OpenRouterProvider().tailor(master="# Ada\n", posting="x")
        self.assertIn("model call failed", str(caught.exception))
