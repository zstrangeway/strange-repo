"""The provider interface, the stub, and the real client.

Nothing here reaches the network. The client is replaced, because the specs
cannot cover this module at all — a suite that called a real model would be
slow, cost somebody money, and test nothing repeatable. `scout-smoke` is what
calls one on purpose, on a free model.
"""

import os
import unittest
import unittest.mock

import httpx2
import openai
from support import InAScratchHome

from scout import providers
from scout.errors import ScoutError
from scout.providers.openrouter import DEFAULT_MODEL, OpenRouterProvider
from scout.providers.prompt import SYSTEM


class Loading(unittest.TestCase):
    def test_the_default_is_openrouter(self):
        self.assertEqual(providers.load().name, "openrouter")

    def test_the_stub_can_be_asked_for_by_name(self):
        self.assertEqual(providers.load("fake").name, "fake")

    def test_a_provider_that_does_not_exist_says_which_one_does(self):
        with self.assertRaises(ScoutError) as caught:
            providers.load("ollama")
        self.assertIn("openrouter", caught.exception.detail)


class TheStub(InAScratchHome):
    def test_it_returns_the_master_when_nothing_was_asked_for(self):
        # So a scenario that does not care what the model said does not have
        # to invent a draft.
        self.assertEqual(
            providers.load("fake").tailor(master="# Ada\n", posting="x"), "# Ada\n"
        )


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

    def test_the_default_model_is_a_claude(self):
        # One provider is not one model. The router is the only client, and
        # Sonnet 5 is still what it asks for by default.
        self.assertEqual(OpenRouterProvider().model, "anthropic/claude-sonnet-5")
        self.assertEqual(DEFAULT_MODEL, "anthropic/claude-sonnet-5")

    def test_the_model_can_be_set_from_the_environment(self):
        with unittest.mock.patch.dict(os.environ, {"SCOUT_MODEL": "openai/gpt-5"}):
            self.assertEqual(OpenRouterProvider().model, "openai/gpt-5")

    def test_a_missing_key_is_caught_before_a_connection_is_opened(self):
        os.environ.pop("OPENROUTER_API_KEY")
        with (
            unittest.mock.patch("scout.providers.openrouter.openai.OpenAI") as client,
            self.assertRaises(ScoutError) as caught,
        ):
            OpenRouterProvider().tailor(master="# Ada\n", posting="x")
        client.assert_not_called()
        self.assertIn("OPENROUTER_API_KEY", str(caught.exception))

    def test_it_sends_the_shared_instruction(self):
        # The prompt lives in its own module so a second provider cannot
        # quietly drift to a different version of it. This asserts the one
        # that exists actually uses it.
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
