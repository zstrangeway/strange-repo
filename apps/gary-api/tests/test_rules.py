"""Grading, and the tool calls the engines refuse.

The four-degree ladder is the one place gary implements a rule with real
edges, so the edges are pinned here rather than sampled by a scenario that
rolls whatever it rolls. The refusals below are what a model gets when it
asks for something that reads like a check and is not.
"""

import asyncio
import unittest
import uuid

from gary_api import narration, play, systems
from gary_api.auth import Refusal
from gary_api.dice import Roll
from gary_api.systems.base import D20Ruleset, Degree, FourDegrees


def rolled(total, natural=10):
    return Roll("1d20", (natural,), total - natural, total, "")


class GradingTests(unittest.TestCase):
    def setUp(self):
        self.rules = FourDegrees()

    def test_ten_over_is_a_critical_success(self):
        self.assertEqual(self.rules.grade(rolled(25), 15), Degree.CRITICAL_SUCCESS)

    def test_meeting_it_is_a_success(self):
        self.assertEqual(self.rules.grade(rolled(15), 15), Degree.SUCCESS)

    def test_one_under_is_a_failure(self):
        self.assertEqual(self.rules.grade(rolled(14), 15), Degree.FAILURE)

    def test_ten_under_is_a_critical_failure(self):
        self.assertEqual(self.rules.grade(rolled(5), 15), Degree.CRITICAL_FAILURE)

    def test_a_natural_twenty_shifts_one_step_better(self):
        self.assertEqual(self.rules.grade(rolled(14, 20), 15), Degree.SUCCESS)

    def test_a_natural_one_shifts_one_step_worse(self):
        self.assertEqual(self.rules.grade(rolled(25, 1), 15), Degree.SUCCESS)

    def test_a_natural_twenty_on_a_hopeless_check_is_still_not_a_triumph(self):
        # The shift applies after the comparison rather than instead of it,
        # which is the whole reason it is worth implementing rather than
        # describing.
        self.assertEqual(self.rules.grade(rolled(3, 20), 40), Degree.FAILURE)

    def test_the_ladder_does_not_fall_off_the_top(self):
        self.assertEqual(
            self.rules.shift(Degree.CRITICAL_SUCCESS, 1), Degree.CRITICAL_SUCCESS
        )

    def test_the_ladder_does_not_fall_off_the_bottom(self):
        self.assertEqual(
            self.rules.shift(Degree.CRITICAL_FAILURE, -1), Degree.CRITICAL_FAILURE
        )

    def test_a_ruleset_that_forgot_to_grade_says_so(self):
        with self.assertRaises(NotImplementedError):
            D20Ruleset().grade(rolled(10), 10)

    def test_no_modifier_leaves_it_out_of_the_notation(self):
        outcome = systems.ruleset("dnd-5e").resolve(dc=10, modifier=0, reason="Spot")
        self.assertEqual(outcome.roll.notation, "1d20")

    def test_a_modifier_is_signed_into_the_notation(self):
        outcome = systems.ruleset("dnd-5e").resolve(dc=10, modifier=-2, reason="Spot")
        self.assertEqual(outcome.roll.notation, "1d20-2")


class Stub:
    """Just enough of a campaign and a character for the refusals below.

    None of these reach the database: the engines refuse before anything is
    written, which is the point of validating there rather than at the far end.
    """

    system_slug = "dnd-5e"

    def __init__(self, name="Bramble"):
        self.id = uuid.uuid4()
        self.name = name


class _Fights:
    """Just enough database for the refusals that never reach one.

    A fight that is refused for its arguments is refused before anything is
    read, so what this has to answer is "nothing here yet" and no more.
    """

    async def scalars(self, *_args, **_kwargs):
        return []

    async def scalar(self, *_args, **_kwargs):
        return 0

    def add(self, *_args, **_kwargs):
        pass

    async def flush(self):
        pass


class RefusedCallTests(unittest.TestCase):
    def run_call(self, name, arguments):
        who = Stub()
        return asyncio.run(
            play._run(
                None,
                Stub(),
                [who],
                narration.Call(name, arguments),
                uuid.uuid4(),
                uuid.uuid4(),
            )
        )

    def test_a_difficulty_that_is_not_a_number(self):
        result, frames = self.run_call(
            "check", {"characters": ["Bramble"], "dc": "hard", "reason": "Spot"}
        )
        self.assertTrue(result.failed)
        self.assertIn("difficulty class", result.summary)
        self.assertTrue(frames)

    def test_an_ability_this_system_does_not_have(self):
        # Gary names an ability and the sheet supplies the number, so the one
        # thing it can get wrong here is naming an ability that does not
        # exist. Refused rather than silently rolled flat, which would look
        # exactly like a check nobody meant to modify.
        result, _ = self.run_call(
            "check", {"characters": ["Bramble"], "ability": "luck", "dc": 15}
        )
        self.assertTrue(result.failed)
        self.assertIn("luck", result.summary)

    def test_a_check_with_nobody_in_it(self):
        result, _ = self.run_call("check", {"characters": [], "dc": 15})
        self.assertTrue(result.failed)
        self.assertIn("somebody", result.summary)

    def test_a_character_who_is_not_here(self):
        result, _ = self.run_call("check", {"characters": ["Nobody"], "dc": 15})
        self.assertTrue(result.failed)
        self.assertIn("Nobody", result.summary)

    def test_one_name_rather_than_a_list_is_taken_as_one_name(self):
        # Models do this. Refusing would be technically correct and would
        # cost the player a turn over a bracket.
        result, _ = self.run_call(
            "check", {"characters": "Nobody", "dc": 15}
        )
        self.assertTrue(result.failed)
        self.assertIn("Nobody", result.summary)

    def test_a_tool_that_does_not_exist(self):
        # A model can ask for anything. What it gets back is a refusal it can
        # narrate around, not a traceback.
        result, _ = self.run_call("summon_dragon", {})
        self.assertTrue(result.failed)
        self.assertIn("summon_dragon", result.summary)

    def test_notation_that_is_not_dice(self):
        result, _ = self.run_call("roll", {"notation": "1d20+lots"})
        self.assertTrue(result.failed)

    def test_every_tool_the_narrator_is_offered_is_one_gary_answers(self):
        # A tool in the contract that the router does not implement is a tool
        # the model will call and nothing will do.
        #
        # The fight tools need a database to answer at all — whether there is
        # a fight is a fold over the log — so here they only have to be
        # *reached*. Falling through to the bottom of the chain is what this
        # is looking for, and that returns rather than raising.
        for name in narration.TOOLS:
            with self.subTest(name=name):
                try:
                    result, _ = self.run_call(name, {})
                except Exception:
                    continue
                self.assertNotIn("has no", result.summary)


if __name__ == "__main__":
    unittest.main()


class FightTests(unittest.TestCase):
    """The refusals a fight can produce before it touches a database.

    Everything reachable without one is here; the rest is in
    ``features/combat.feature``, which has a real log to fold.
    """

    def refusing(self, call, **arguments):
        return asyncio.run(
            play._run(
                _Fights(),
                Stub(),
                [Stub()],
                narration.Call(call, arguments),
                uuid.uuid4(),
                uuid.uuid4(),
            )
        )

    def test_a_fight_with_nothing_in_it(self):
        result, _ = self.refusing("begin_combat", adversaries=[])
        self.assertTrue(result.failed)
        self.assertIn("something to fight", result.summary)

    def test_an_adversary_that_is_not_a_shape(self):
        result, _ = self.refusing("begin_combat", adversaries=["a wolf"])
        self.assertTrue(result.failed)
        self.assertIn("name and a shape", result.summary)

    def test_an_adversary_with_no_name(self):
        result, _ = self.refusing("begin_combat", adversaries=[{"hit_points": 4}])
        self.assertTrue(result.failed)
        self.assertIn("name", result.summary)

    def test_an_adversary_with_hit_points_that_are_not_a_number(self):
        result, _ = self.refusing(
            "begin_combat",
            adversaries=[{"name": "wolf", "hit_points": "lots", "armour_class": 12}],
        )
        self.assertTrue(result.failed)
        self.assertIn("whole number", result.summary)

    def test_attacking_when_there_is_no_fight(self):
        result, _ = self.refusing("attack", attacker="Gus", target="wolf")
        self.assertTrue(result.failed)
        self.assertIn("no fight", result.summary)

    def test_ending_a_turn_when_there_is_no_fight(self):
        result, _ = self.refusing("end_turn")
        self.assertTrue(result.failed)
        self.assertIn("no fight", result.summary)


class SheetTests(unittest.TestCase):
    """What may be written on a sheet, checked against the system's own list."""

    def setUp(self):
        # Any registered system would do; this asks the registry for one
        # rather than naming it, the way everything outside the package has
        # to — see test_pluggable.
        self.ruleset = next(iter(systems.rulesets()))

    def sheet(self, wanted):
        return play._sheet_for(self.ruleset, wanted)

    def test_nobody_has_to_supply_any(self):
        # A campaign started before scores existed has characters who never
        # gave any, and not everybody wants to arrange six numbers to play.
        made = self.sheet(None)
        self.assertEqual(set(made), set(self.ruleset.abilities))
        self.assertEqual(set(made.values()), {self.ruleset.default_score})

    def test_what_is_supplied_is_kept(self):
        ability = self.ruleset.abilities[0]
        self.assertEqual(self.sheet({ability: 16})[ability], 16)

    def test_an_ability_this_system_does_not_have(self):
        with self.assertRaises(Refusal):
            self.sheet({"nonsense": 16})

    def test_a_score_outside_the_range(self):
        with self.assertRaises(Refusal):
            self.sheet({self.ruleset.abilities[0]: self.ruleset.scores[1] + 1})

    def test_a_boolean_is_not_a_score(self):
        # Pydantic types the field as int and is happy to make one out of a
        # boolean, so `{"dex": true}` arrives here as a dexterity of 1 rather
        # than as a rejection.
        with self.assertRaises(Refusal):
            self.sheet({self.ruleset.abilities[0]: True})
