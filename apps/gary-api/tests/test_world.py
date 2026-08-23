"""The world's validation and projection, without a database in the way.

``clean`` is where an event is refused before it is written, and refusing is
the whole reason the log is worth folding: an event that cannot be applied is
a hole in the world's history. Every refusal below is one a model could
plausibly cause.
"""

import unittest
import uuid

from gary_api import world


class Sheet:
    """A character as far as the projection is concerned."""

    def __init__(
        self, name="Bramble", max_hp=8, played_by="gary", level=1, experience=0
    ):
        self.id = uuid.uuid4()
        self.name = name
        self.character_class = "rogue"
        self.level = level
        self.experience = experience
        self.max_hp = max_hp
        self.played_by = played_by


class Event:
    def __init__(self, kind, payload):
        self.kind = kind
        self.payload = payload


class AdvancementTests(unittest.TestCase):
    """The two halves of advancement, where the specs cannot reach them."""

    def test_a_level_below_one_is_refused(self):
        # Zero gets past the "whole number of at least 0" check every other
        # count uses, and a level 0 character is not a thing.
        with self.assertRaises(world.WorldError):
            world.clean(
                world.LEVELLED,
                {
                    "character_id": str(uuid.uuid4()),
                    "level": 0,
                    "hit_points": 3,
                },
            )

    def test_advancement_for_somebody_who_has_gone_is_skipped(self):
        # An append-only log keeps what happened to a character who is no
        # longer here. Folding it has to step over them rather than fail.
        gone = str(uuid.uuid4())
        world_now = world.project(
            [Sheet()],
            [
                Event(world.EARNED, {"character_id": gone, "amount": 300, "reason": "x"}),
                Event(
                    world.LEVELLED,
                    {"character_id": gone, "level": 2, "hit_points": 4},
                ),
            ],
        )
        self.assertEqual(world_now.party[0].experience, 0)
        self.assertEqual(world_now.party[0].level, 1)


class CleanTests(unittest.TestCase):
    def test_refuses_a_kind_that_is_not_a_thing_that_happens(self):
        with self.assertRaises(world.WorldError):
            world.clean("party-teleported", {})

    def test_refuses_a_move_to_nowhere(self):
        for payload in ({}, {"place": ""}, {"place": "   "}, {"place": 4}):
            with self.subTest(payload=payload), self.assertRaises(world.WorldError):
                world.clean(world.MOVED, payload)

    def test_trims_a_place(self):
        self.assertEqual(
            world.clean(world.MOVED, {"place": "  the stair "}),
            {"place": "the stair"},
        )

    def test_refuses_a_fact_without_both_halves(self):
        for payload in ({"key": "a"}, {"value": "b"}, {"key": "", "value": "b"}):
            with self.subTest(payload=payload), self.assertRaises(world.WorldError):
                world.clean(world.REMEMBERED, payload)

    def test_forgetting_needs_only_a_key(self):
        self.assertEqual(world.clean(world.FORGOTTEN, {"key": "a"}), {"key": "a"})

    def test_refuses_an_amount_that_is_not_a_whole_number(self):
        who = str(uuid.uuid4())
        for amount in (-1, "4", 1.5, None):
            with self.subTest(amount=amount), self.assertRaises(world.WorldError):
                world.clean(world.DAMAGED, {"character_id": who, "amount": amount})

    def test_refuses_true_as_an_amount(self):
        # bool is an int in Python, and True would otherwise arrive as 1 —
        # which is a number nobody meant.
        with self.assertRaises(world.WorldError):
            world.clean(
                world.DAMAGED,
                {"character_id": str(uuid.uuid4()), "amount": True},
            )

    def test_allows_nothing_at_all(self):
        who = str(uuid.uuid4())
        self.assertEqual(
            world.clean(world.HEALED, {"character_id": who, "amount": 0}),
            {"character_id": who, "amount": 0},
        )

    def test_refuses_something_that_is_not_a_character(self):
        with self.assertRaises(world.WorldError):
            world.clean(world.DAMAGED, {"character_id": "Bramble", "amount": 1})

    def test_lowercases_a_condition(self):
        who = str(uuid.uuid4())
        self.assertEqual(
            world.clean(
                world.AFFLICTED, {"character_id": who, "condition": "Frightened"}
            )["condition"],
            "frightened",
        )

    def test_refuses_time_running_backwards(self):
        with self.assertRaises(world.WorldError):
            world.clean(world.ELAPSED, {"minutes": -5})

    def test_treats_a_missing_payload_as_empty(self):
        with self.assertRaises(world.WorldError):
            world.clean(world.MOVED, None)


class ProjectionTests(unittest.TestCase):
    def test_a_world_with_nothing_in_it(self):
        state = world.project([], [])
        self.assertEqual(state.place, "")
        self.assertEqual(state.minutes, 0)
        self.assertEqual(state.facts, {})
        self.assertEqual(state.party, [])

    def test_everyone_starts_at_full(self):
        sheet = Sheet(max_hp=11)
        member = world.project([sheet], []).party[0]
        self.assertEqual(member.hp, 11)
        self.assertFalse(member.down)

    def test_an_event_naming_nobody_is_skipped_rather_than_fatal(self):
        # A character can be removed and the events they caused stay in the
        # history. Skipping is the correct reading of an append-only log.
        sheet = Sheet()
        state = world.project(
            [sheet],
            [Event(world.DAMAGED, {"character_id": str(uuid.uuid4()), "amount": 4})],
        )
        self.assertEqual(state.party[0].hp, sheet.max_hp)

    def test_relieving_a_condition_nobody_has_changes_nothing(self):
        sheet = Sheet()
        state = world.project(
            [sheet],
            [Event(world.RELIEVED, {"character_id": str(sheet.id), "condition": "x"})],
        )
        self.assertEqual(state.party[0].conditions, [])

    def test_forgetting_something_never_known_changes_nothing(self):
        state = world.project([], [Event(world.FORGOTTEN, {"key": "nope"})])
        self.assertEqual(state.facts, {})

    def test_member_finds_nobody(self):
        self.assertIsNone(world.project([], []).member("whoever"))


class RenderTests(unittest.TestCase):
    def test_says_when_there_is_nobody(self):
        self.assertIn("nobody yet", world.render(world.project([], [])))

    def test_says_where_it_does_not_know(self):
        self.assertIn("not yet established", world.render(world.project([], [])))

    def test_names_the_down_and_the_afflicted(self):
        sheet = Sheet()
        state = world.project(
            [sheet],
            [
                Event(world.DAMAGED, {"character_id": str(sheet.id), "amount": 99}),
                Event(
                    world.AFFLICTED,
                    {"character_id": str(sheet.id), "condition": "prone"},
                ),
            ],
        )
        written = world.render(state)
        self.assertIn("down", written)
        self.assertIn("prone", written)
        self.assertIn("0/8", written)

    def test_lists_facts_in_a_stable_order(self):
        state = world.project(
            [],
            [
                Event(world.REMEMBERED, {"key": "b", "value": "2"}),
                Event(world.REMEMBERED, {"key": "a", "value": "1"}),
            ],
        )
        written = world.render(state)
        self.assertLess(written.index("a: 1"), written.index("b: 2"))


if __name__ == "__main__":
    unittest.main()


class WhoPlaysThemTests(unittest.TestCase):
    """The one fact about the party gary must never lose track of."""

    def test_the_projection_carries_it_through(self):
        world_now = world.project([Sheet(played_by="player")], [])
        self.assertEqual(world_now.party[0].played_by, "player")

    def test_the_player_is_named_as_off_limits(self):
        text = world.render(world.project([Sheet(name="Bramble", played_by="player")], []))
        self.assertIn("Bramble", text)
        self.assertIn("never decide what they do", text)

    def test_a_companion_is_offered_to_gary(self):
        text = world.render(world.project([Sheet(name="Maud")], []))
        self.assertIn("Maud", text)
        self.assertIn("yours to play", text)


class FightEventTests(unittest.TestCase):
    """The parts of a fight the log refuses, and the one it has to survive."""

    def test_an_event_naming_neither_side(self):
        with self.assertRaises(world.WorldError):
            world.clean(world.DAMAGED, {"amount": 2})

    def test_an_event_naming_both_sides(self):
        # Not pedantry: which table to look the id up in is the whole content
        # of the distinction, and an event claiming both answers neither.
        with self.assertRaises(world.WorldError):
            world.clean(
                world.DAMAGED,
                {
                    "character_id": str(uuid.uuid4()),
                    "adversary_id": str(uuid.uuid4()),
                    "amount": 2,
                },
            )

    def test_a_fight_with_nobody_in_it(self):
        with self.assertRaises(world.WorldError):
            world.clean(world.FOUGHT, {"order": []})

    def test_a_turn_ending_carries_nothing(self):
        self.assertEqual(world.clean(world.TURNED, {"anything": 1}), {})


class AdvanceTests(unittest.TestCase):
    """Moving a fight on, including the two edges a game reaches quickly."""

    def _fight(self, hp):
        state = world.World(
            party=[
                world.Member(id=str(n), name=f"P{n}", max_hp=8, hp=points)
                for n, points in enumerate(hp)
            ]
        )
        state.fight = world.Fight(order=[str(n) for n in range(len(hp))])
        return state

    def test_skips_whoever_is_down(self):
        # A fight that stopped on somebody at nought and waited for them to
        # act would never move again.
        state = self._fight([8, 0, 8])
        world._advance(state)
        self.assertEqual(state.fight.whose, "2")

    def test_gives_up_when_everybody_is_down(self):
        # Reached only in the moment before the engine ends the fight. A fold
        # over a log is not the place to start refusing history, so it stops
        # rather than looping.
        state = self._fight([0, 0])
        world._advance(state)
        self.assertEqual(state.fight.round, 2)

    def test_does_nothing_when_there_is_no_fight(self):
        state = world.World()
        world._advance(state)
        self.assertIsNone(state.fight)

    def test_an_order_naming_somebody_who_is_gone_is_skipped(self):
        # A character can be removed and the events they caused stay in the
        # history, which is the correct reading of an append-only log.
        state = self._fight([8, 8])
        state.fight.order.append(str(uuid.uuid4()))
        self.assertIsNone(state.foe("nobody"))
        self.assertEqual(world.render(state).count("P0"), 2)


class FoeLookupTests(unittest.TestCase):
    def test_looks_past_the_first_one(self):
        # Two, so the loop has to continue rather than answering from where
        # it started — which one enemy would never prove.
        state = world.World(
            enemies=[
                world.Foe(id="1", name="wolf", max_hp=4, hp=4),
                world.Foe(id="2", name="bear", max_hp=9, hp=9),
            ]
        )
        self.assertEqual(state.foe("2").name, "bear")
        self.assertIsNone(state.foe("3"))
