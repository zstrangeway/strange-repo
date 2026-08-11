"""The hand-run check that talks to a real model.

It is the only thing standing between "the specs pass against a double" and
"a model can actually hold up its end", so the parts that decide whether it
reports the truth are worth pinning — particularly its two refusals to run.
A smoke test that passes by doing nothing is worse than not having one.
"""

import unittest
from unittest.mock import patch

import httpx

from gary_api import narration, smoke, systems


class Stub:
    """A narrator that yields exactly what a test stages."""

    name = "stub"

    def __init__(self, script, explode=None):
        self.script = script
        self.explode = explode
        self.answered = []

    def sanitise(self, message):
        return message

    async def narrate(self, prompt):
        if self.explode:
            raise self.explode
        for event in self.script:
            results = yield event
            if results is not None:
                self.answered.append(results)


def run(script=None, explode=None, opening=False):
    stub = Stub(script or [narration.Said("A door.")], explode)
    with patch.object(narration, "narrator", lambda model=None: stub):
        code = __import__("asyncio").run(smoke.play("a/model", opening))
    return code, stub


class GuardTests(unittest.TestCase):
    def test_refuses_without_a_key(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(smoke.main(), 2)

    def test_refuses_to_test_the_double_against_itself(self):
        # GM_FAKE would make this pass while proving nothing, which is the
        # exact failure it exists to catch.
        with patch.dict(
            "os.environ", {"OPENROUTER_API_KEY": "sk-or-test", "GM_FAKE": "1"}
        ):
            self.assertEqual(smoke.main(), 2)


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.rules = systems.rulesets()[0]
        self.state = smoke.a_world()
        self.log = []

    def call(self, name, arguments):
        return smoke.run_tool(
            narration.Call(name, arguments), self.rules, self.state, self.log
        )

    def test_a_roll_goes_through_the_dice(self):
        summary, made = self.call("roll", {"notation": "1d20+3", "reason": "Spot"})
        self.assertIn("came up", summary)
        self.assertEqual(made.notation, "1d20+3")

    def test_a_check_goes_through_the_rules(self):
        summary, outcome = self.call("check", {"character": "Bramble", "dc": 15})
        self.assertIn(outcome.degree.value, summary)
        self.assertIn(outcome.degree, self.rules.degrees)

    def test_moving_changes_the_world_it_was_given(self):
        self.call("move_party", {"place": "the stair"})
        self.assertEqual(self.state.place, "the stair")

    def test_remembering_changes_the_world_it_was_given(self):
        self.call("remember", {"key": "bell-rings", "value": "9"})
        self.assertEqual(self.state.facts["bell-rings"], "9")

    def test_time_accumulates(self):
        before = self.state.minutes
        self.call("pass_time", {"minutes": 15})
        self.assertEqual(self.state.minutes, before + 15)

    def test_hit_points_and_conditions_are_acknowledged(self):
        self.assertIn("damage", self.call("damage", {"character": "Bramble"})[0])
        self.assertIn("condition", self.call("add_condition", {})[0])

    def test_a_tool_gary_does_not_have(self):
        summary, _ = self.call("summon_dragon", {})
        self.assertIn("summon_dragon", summary)

    def test_something_the_engines_refuse(self):
        summary, _ = self.call("roll", {"notation": "1d20+lots"})
        self.assertTrue(summary.startswith("refused:"))

    def test_every_call_is_logged(self):
        self.call("pass_time", {"minutes": 1})
        self.call("pass_time", {"minutes": 1})
        self.assertEqual(len(self.log), 2)

    def test_every_tool_the_model_is_offered_is_answered(self):
        # A tool in the contract that this script cannot answer would make the
        # smoke run report a failure the real router does not have.
        for name in narration.TOOLS:
            with self.subTest(name=name):
                summary, _ = self.call(name, {"character": "Bramble"})
                self.assertNotIn("gary has no", summary)


class PlayTests(unittest.TestCase):
    def test_reports_a_turn_that_used_no_tools(self):
        code, _ = run([narration.Said("It is quiet.")])
        self.assertEqual(code, 0)

    def test_answers_the_tools_it_is_asked_for(self):
        code, stub = run(
            [
                narration.Calls(
                    [narration.Call("check", {"character": "Bramble", "dc": 15})]
                ),
                narration.Said("You fail."),
            ]
        )
        self.assertEqual(code, 0)
        self.assertTrue(stub.answered)
        self.assertEqual(len(stub.answered[0]), 1)

    def test_reports_a_roll_as_well_as_a_check(self):
        # A roll has no degree to report, which is a different path through
        # the summary than a graded check.
        code, _ = run(
            [
                narration.Calls([narration.Call("roll", {"notation": "1d20"})]),
                narration.Said("Seventeen."),
            ]
        )
        self.assertEqual(code, 0)

    def test_a_refusal_is_reported_rather_than_treated_as_a_failure(self):
        code, _ = run([narration.Refused("Gary would rather not.")])
        self.assertEqual(code, 0)

    def test_an_opening_is_asked_for_without_anybody_having_spoken(self):
        # The one turn with an empty transcript. What it sends is the router's
        # own instruction rather than a copy, so a smoke run cannot report on
        # a prompt gary does not use.
        code, stub = run([narration.Said("The causeway.")], opening=True)
        self.assertEqual(code, 0)

    def test_being_unreachable_is_a_failure(self):
        code, _ = run(explode=narration.NarrationError("no route"))
        self.assertEqual(code, 1)


class SpendTests(unittest.TestCase):
    def test_reads_what_the_key_has_spent(self):
        def answered(url, **kwargs):
            return httpx.Response(
                200,
                json={"data": {"usage": 1.25}},
                request=httpx.Request("GET", url),
            )

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}):
            with patch.object(smoke.httpx, "get", answered):
                self.assertEqual(smoke.spend(), 1.25)

    def test_says_nothing_rather_than_guessing_when_it_cannot_tell(self):
        def refused(url, **kwargs):
            return httpx.Response(401, json={}, request=httpx.Request("GET", url))

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-bad"}):
            with patch.object(smoke.httpx, "get", refused):
                self.assertIsNone(smoke.spend())


class MainTests(unittest.TestCase):
    def test_takes_the_model_from_the_command_line(self):
        seen = {}

        async def fake_play(model, opening=False):
            seen["model"] = model
            seen["opening"] = opening
            return 0

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}, clear=True):
            with patch.object(smoke, "play", fake_play):
                with patch.object(smoke, "spend", lambda: 0.5):
                    with patch.object(smoke.sys, "argv", ["smoke", "a/named-model"]):
                        self.assertEqual(smoke.main(), 0)
        self.assertEqual(seen["model"], "a/named-model")
        self.assertFalse(seen["opening"])

    def test_falls_back_to_the_default_model(self):
        seen = {}

        async def fake_play(model, opening=False):
            seen["model"] = model
            return 0

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}, clear=True):
            with patch.object(smoke, "play", fake_play):
                with patch.object(smoke, "spend", lambda: None):
                    with patch.object(smoke.sys, "argv", ["smoke"]):
                        self.assertEqual(smoke.main(), 0)
        self.assertEqual(seen["model"], narration.models.default())

    def test_the_opening_flag_is_not_mistaken_for_a_model(self):
        # `smoke --opening` names no model, and reading the flag as one would
        # ask OpenRouter for a model called "--opening".
        seen = {}

        async def fake_play(model, opening=False):
            seen["model"] = model
            seen["opening"] = opening
            return 0

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}, clear=True):
            with patch.object(smoke, "play", fake_play):
                with patch.object(smoke, "spend", lambda: None):
                    with patch.object(smoke.sys, "argv", ["smoke", "--opening"]):
                        self.assertEqual(smoke.main(), 0)
        self.assertEqual(seen["model"], narration.models.default())
        self.assertTrue(seen["opening"])


if __name__ == "__main__":
    unittest.main()
