"""Which models gary offers, and the one thing it will not offer.

The specs run without a key, so they only ever see the built-in list. The
fetching, the filtering and every way it can go wrong are here — and the
filter is the part worth pinning hardest, because a model that cannot call a
tool does not fail loudly. It narrates a plausible game that nothing is
adjudicating.
"""

import unittest
from unittest.mock import patch

import httpx

from gary_api.narration import models


def row(identifier, tools=True, reasoning=False, prompt="0.000001", completion="0.000004"):
    parameters = []
    if tools:
        parameters.append("tools")
    if reasoning:
        parameters.append("reasoning")
    return {
        "id": identifier,
        "name": identifier.split("/")[-1],
        "pricing": {"prompt": prompt, "completion": completion},
        "context_length": 128000,
        "supported_parameters": parameters,
    }


def served(rows):
    """Stand in for OpenRouter answering with these models."""

    def get(url, **kwargs):
        return httpx.Response(
            200, json={"data": rows}, request=httpx.Request("GET", url)
        )

    return patch.object(models.httpx, "get", get)


class FallbackTests(unittest.TestCase):
    def setUp(self):
        models.forget()

    def tearDown(self):
        models.forget()

    def test_without_a_key_the_built_in_list_is_offered(self):
        # Not an empty list and not an error: a keyless deployment still
        # starts, still shows a menu, and still plays against the double.
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(models.available(), models.BUILT_IN)

    def test_the_built_in_list_suggests_some_but_not_all(self):
        suggested = [model for model in models.BUILT_IN if model.suggested]
        self.assertTrue(suggested)
        self.assertLess(len(suggested), len(models.BUILT_IN))

    def test_openrouter_falling_over_falls_back(self):
        def boom(url, **kwargs):
            raise httpx.ConnectError("no route to host")

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}):
            with patch.object(models.httpx, "get", boom):
                self.assertEqual(models.available(), models.BUILT_IN)

    def test_openrouter_serving_nothing_usable_falls_back(self):
        # Every model refused by the filter is the same situation as no
        # answer at all, and an empty menu would be worse than a stale one.
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}):
            with served([row("someone/text-only", tools=False)]):
                self.assertEqual(models.available(), models.BUILT_IN)


class FetchTests(unittest.TestCase):
    def setUp(self):
        models.forget()

    def tearDown(self):
        models.forget()

    def fetched(self, rows):
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}):
            with served(rows):
                return models.available()

    def test_keeps_only_what_can_call_tools(self):
        found = self.fetched(
            [row("a/can", tools=True), row("b/cannot", tools=False)]
        )
        self.assertEqual([model.id for model in found], ["a/can"])

    def test_prices_are_per_million_tokens(self):
        # Fractions of a cent per token are not something anyone can compare;
        # dollars per million is the unit the difference is legible in.
        found = self.fetched(
            [row("a/one", prompt="0.00000027", completion="0.0000004")]
        )
        self.assertAlmostEqual(found[0].prompt_cost, 0.27)
        self.assertAlmostEqual(found[0].completion_cost, 0.40)

    def test_notes_which_ones_reason(self):
        found = self.fetched([row("a/thinks", reasoning=True)])
        self.assertTrue(found[0].reasons)

    def test_suggestions_come_first_then_the_cheapest(self):
        rows = [
            row("z/dear", completion="0.00009"),
            row("y/cheap", completion="0.000001"),
            row(models.SUGGESTED[0], completion="0.00005"),
        ]
        found = [model.id for model in self.fetched(rows)]
        self.assertEqual(found[0], models.SUGGESTED[0])
        self.assertEqual(found[1:], ["y/cheap", "z/dear"])

    def test_a_row_with_no_id_is_skipped_rather_than_fatal(self):
        found = self.fetched([{"supported_parameters": ["tools"]}, row("a/fine")])
        self.assertEqual([model.id for model in found], ["a/fine"])

    def test_a_row_with_unreadable_pricing_is_skipped(self):
        found = self.fetched([row("a/odd", prompt="free"), row("b/fine")])
        self.assertEqual([model.id for model in found], ["b/fine"])

    def test_the_answer_is_cached(self):
        calls = []

        def counting(url, **kwargs):
            calls.append(url)
            return httpx.Response(
                200, json={"data": [row("a/one")]}, request=httpx.Request("GET", url)
            )

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}):
            with patch.object(models.httpx, "get", counting):
                models.available()
                models.available()
        self.assertEqual(len(calls), 1)

    def test_a_refusal_from_openrouter_falls_back(self):
        def refused(url, **kwargs):
            return httpx.Response(401, json={}, request=httpx.Request("GET", url))

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-bad"}):
            with patch.object(models.httpx, "get", refused):
                self.assertEqual(models.available(), models.BUILT_IN)


class LookupTests(unittest.TestCase):
    def setUp(self):
        models.forget()

    def tearDown(self):
        models.forget()

    def test_finds_one_it_offers(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                models.model(models.BUILT_IN[0].id).id, models.BUILT_IN[0].id
            )

    def test_refuses_one_it_does_not(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(models.ModelError):
                models.model("nobody/cannot-call-tools")

    def test_the_default_is_one_it_offers(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(models.model(models.default()).id, models.default())


if __name__ == "__main__":
    unittest.main()
