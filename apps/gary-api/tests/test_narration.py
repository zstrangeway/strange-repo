"""The double's directive parsing, and which narrator gets built.

The double is spec scaffolding, but it is scaffolding every play scenario
leans on: a directive it silently misreads is a scenario that passes without
exercising what it claims to. So its parsing is pinned here rather than left
to be inferred from the features that use it.
"""

import asyncio
import unittest
from unittest.mock import patch

from gary_api import narration
from gary_api.narration import fake


class DirectiveTests(unittest.TestCase):
    def test_finds_several(self):
        self.assertEqual(
            fake.directives("I look [[roll 1d20 Spot]] and wait [[time 5]]"),
            ["roll 1d20 Spot", "time 5"],
        )

    def test_finds_none(self):
        self.assertEqual(fake.directives("I push open the door"), [])
        self.assertEqual(fake.directives(""), [])
        self.assertEqual(fake.directives(None), [])

    def test_strips_them_out_of_what_is_stored(self):
        # A transcript must never contain scaffolding, or the specs would be
        # asserting against text no player ever typed.
        self.assertEqual(
            fake.strip("I search the room [[roll 1d20+3 Perception]]"),
            "I search the room",
        )

    def test_stripping_leaves_ordinary_text_alone(self):
        self.assertEqual(fake.strip("I push open the door"), "I push open the door")


class CallTests(unittest.TestCase):
    def test_a_roll(self):
        call = fake._call("roll 1d20+3 Perception")
        self.assertEqual(call.name, "roll")
        self.assertEqual(call.arguments["notation"], "1d20+3")
        self.assertEqual(call.arguments["reason"], "Perception")

    def test_a_check(self):
        call = fake._call("check Bramble 15 Perception")
        self.assertEqual(call.name, "check")
        self.assertEqual(call.arguments["character"], "Bramble")
        self.assertEqual(call.arguments["dc"], 15)

    def test_a_check_with_a_difficulty_that_is_not_a_number(self):
        # Left as written rather than coerced, so it reaches the same refusal
        # a real model's nonsense would.
        self.assertEqual(fake._call("check Bramble hard Spot").arguments["dc"], "hard")

    def test_a_move(self):
        self.assertEqual(
            fake._call("move the belfry stair").arguments["place"], "the belfry stair"
        )

    def test_remembering(self):
        call = fake._call("remember bell-rings=4")
        self.assertEqual(call.arguments, {"key": "bell-rings", "value": "4"})

    def test_damage_and_healing(self):
        self.assertEqual(fake._call("damage Bramble 4").name, "damage")
        self.assertEqual(fake._call("heal Bramble 2").arguments["amount"], 2)

    def test_damage_of_something_that_is_not_a_number(self):
        self.assertEqual(fake._call("damage Bramble lots").arguments["amount"], "lots")

    def test_conditions_both_ways(self):
        self.assertEqual(fake._call("afflict B frightened").name, "add_condition")
        self.assertEqual(fake._call("relieve B frightened").name, "remove_condition")

    def test_time(self):
        self.assertEqual(fake._call("time 30").arguments["minutes"], 30)
        self.assertEqual(fake._call("time soon").arguments["minutes"], "soon")

    def test_something_that_is_not_a_tool(self):
        self.assertIsNone(fake._call("refuse"))
        self.assertIsNone(fake._call("wibble about"))


def a_prompt(message):
    return narration.Prompt(
        briefing="You are running a game.",
        system_slug="dnd-5e",
        module_slug="the-drowned-belfry",
        module_title="The Drowned Belfry",
        module_premise="A bell rings under the water.",
        world="Where the party is: the causeway",
        message=message,
    )


async def drain(message, limit=50):
    """Everything the double yields, with tool calls answered as done."""
    told = []
    generator = fake.FakeNarrator().narrate(a_prompt(message))
    sending = None
    while len(told) < limit:
        try:
            event = await generator.asend(sending)
        except StopAsyncIteration:
            break
        told.append(event)
        sending = None
        if isinstance(event, narration.Calls):
            sending = [
                narration.Result(call, "it worked") for call in event.calls
            ]
    await generator.aclose()
    return told


class DoubleTests(unittest.TestCase):
    def test_says_something_in_more_than_one_piece(self):
        told = asyncio.run(drain("I push open the door"))
        said = [event for event in told if isinstance(event, narration.Said)]
        self.assertGreater(len(said), 1)
        self.assertIn("door", "".join(event.text for event in said))

    def test_a_refusal_ends_the_turn(self):
        # Nothing after a refusal. The router stops asking the moment it sees
        # one, so this is the contract that makes that safe.
        told = asyncio.run(drain("something awful [[refuse]]"))
        self.assertEqual(len(told), 1)
        self.assertIsInstance(told[0], narration.Refused)

    def test_being_unreachable_raises_rather_than_yielding(self):
        with self.assertRaises(narration.NarrationError):
            asyncio.run(drain("I push open the door [[fail]]"))

    def test_asks_for_what_the_directive_named(self):
        told = asyncio.run(drain("I look [[roll 1d20+3 Spot]]"))
        calls = [event for event in told if isinstance(event, narration.Calls)]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].calls[0].name, "roll")

    def test_narrates_what_a_tool_came_back_with(self):
        told = asyncio.run(drain("I look [[roll 1d20 Spot]]"))
        said = "".join(
            event.text for event in told if isinstance(event, narration.Said)
        )
        self.assertIn("it worked", said)

    def test_says_so_when_a_tool_would_not(self):
        async def refused():
            generator = fake.FakeNarrator().narrate(a_prompt("I look [[roll bad x]]"))
            told = []
            sending = None
            while len(told) < 20:
                try:
                    event = await generator.asend(sending)
                except StopAsyncIteration:
                    break
                told.append(event)
                sending = None
                if isinstance(event, narration.Calls):
                    sending = [
                        narration.Result(call, "not dice", failed=True)
                        for call in event.calls
                    ]
            await generator.aclose()
            return told

        said = "".join(
            event.text
            for event in asyncio.run(refused())
            if isinstance(event, narration.Said)
        )
        self.assertIn("does not work", said)

    def test_a_message_that_is_only_a_directive_still_narrates(self):
        told = asyncio.run(drain("[[time 5]]"))
        self.assertTrue([e for e in told if isinstance(e, narration.Said)])


class SelectionTests(unittest.TestCase):
    def setUp(self):
        narration.narrator.cache_clear()

    def tearDown(self):
        narration.narrator.cache_clear()

    def test_faking_when_told_to(self):
        with patch.dict("os.environ", {"GM_FAKE": "1"}):
            self.assertTrue(narration.faking())
            self.assertIsInstance(narration.narrator(), fake.FakeNarrator)

    def test_not_faking_otherwise(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(narration.faking())

    def test_the_default_model_is_the_one_we_meant(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(narration.model(), narration.DEFAULT_MODEL)

    def test_the_model_can_be_changed(self):
        with patch.dict("os.environ", {"GM_MODEL": "anthropic/claude-sonnet-5"}):
            self.assertEqual(narration.model(), "anthropic/claude-sonnet-5")

    def test_refuses_to_build_a_real_narrator_without_a_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(narration.NarrationError):
                narration.narrator()

    def test_reports_the_double(self):
        with patch.dict("os.environ", {"GM_FAKE": "1"}):
            narration.report_configuration()

    def test_reports_a_missing_key_rather_than_refusing_to_start(self):
        # The rest of gary works without a narrator, and somebody has to be
        # able to sign in to fix it — but it must not be discovered by a
        # player halfway through a sentence.
        with patch.dict("os.environ", {}, clear=True):
            narration.report_configuration()


if __name__ == "__main__":
    unittest.main()
