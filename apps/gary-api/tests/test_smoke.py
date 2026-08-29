"""The hand-run check that talks to a real model.

It is the only thing standing between "the specs pass against a double" and
"a model can actually hold up its end", so the parts that decide whether it
reports the truth are worth pinning — particularly its two refusals to run.
A smoke test that passes by doing nothing is worse than not having one.
"""

import unittest
from unittest.mock import patch

import httpx

from gary_api import dice, narration, smoke, systems, world


class Stub:
    """A narrator that yields exactly what a test stages."""

    name = "stub"

    def __init__(self, script, explode=None):
        self.script = script
        self.explode = explode
        self.answered = []
        self.prompt = None

    def sanitise(self, message):
        return message

    async def _drive(self, prompt):
        self.prompt = prompt
        if self.explode:
            raise self.explode
        for event in self.script:
            results = yield event
            if results is not None:
                self.answered.append(results)

    def narrate(self, prompt):
        return self._drive(prompt)

    def close(self, prompt):
        # The same driving, because that is the real contract: close is
        # asend-driven exactly as narrate is and differs only in the tools
        # offered and what it ends with. A double that drove them differently
        # would let a bug in the caller through.
        return self._drive(prompt)


# What a well-behaved model ends each pass with. A close ends with a Recap
# where a turn ends with prose, so a script that ends the wrong way is
# testing a shape the narrator cannot produce.
ENDINGS = {
    False: narration.Said("Something happens."),
    True: narration.Recap("It ended."),
}


def run(script=None, explode=None, scene="turn"):
    closing = smoke.SCENES[scene].closing
    stub = Stub(script or [ENDINGS[closing]], explode)
    with patch.object(narration, "narrator", lambda model=None: stub):
        code = __import__("asyncio").run(smoke.play("a/model", scene))
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
        self.state = smoke.SCENES["turn"].world()
        self.log = []
        # Seeded, so a fight resolves the same way every run. Without this
        # whether a swing lands is chance, and a test that sometimes covers
        # the hit and sometimes the miss is one that sometimes passes.
        self.seed("1234")

    def seed(self, value):
        patcher = patch.dict("os.environ", {"DICE_SEED": value})
        patcher.start()
        self.addCleanup(patcher.stop)
        dice.configure()
        self.addCleanup(dice.reseed)

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
        # The standing number, not only the delta — the router answers this
        # way now, and a harness that said "noted as damaged" would be back
        # to letting a model keep its own books.
        hurt, _ = self.call("damage", {"character": "Bramble", "amount": 2})
        self.assertIn("Bramble took 2", hurt)
        self.assertIn("now on 4 of 8", hurt)
        self.assertIn("condition", self.call("add_condition", {})[0])

    def test_healing_gives_them_back_and_says_where_that_leaves_them(self):
        back, _ = self.call("heal", {"character": "Bramble", "amount": 1})
        self.assertIn("Bramble recovered 1", back)
        self.assertIn("now on 7 of 8", back)

    def test_hurting_somebody_who_is_not_here_still_answers(self):
        summary, _ = self.call("damage", {"character": "a ghost", "amount": 2})
        self.assertIn("a ghost took 2", summary)

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

    def test_an_ability_this_system_does_not_have_is_refused_here_too(self):
        # Found by a real run: a model asked for a check against a skill
        # rather than an ability, and this script graded it. The router
        # refuses, so a smoke run that did not was reporting a turn that
        # production would have sent back.
        summary, _ = self.call(
            "check", {"characters": ["Bramble"], "ability": "investigation", "dc": 15}
        )
        self.assertIn("refused", summary)
        self.assertIn("investigation", summary)

    def test_a_modifier_from_the_model_is_ignored(self):
        # The router never takes one. A harness that did would let a model
        # quietly decide what a check was worth and still look clean.
        generous, _ = self.call(
            "check", {"characters": ["Bramble"], "dc": 15, "modifier": 100}
        )
        self.assertNotIn("refused", generous)

    def closing_call(self, name, arguments):
        return smoke.run_tool(
            narration.Call(name, arguments),
            self.rules,
            self.state,
            self.log,
            closing=True,
        )

    def test_a_tool_outside_the_closing_set_is_refused_while_closing(self):
        # scenes.close_scene refuses these, so a harness that answered them
        # would show a model reconciling cleanly when production would have
        # sent it back — the same failure the ability refusal exists for.
        for name in ("roll", "check", "award_experience", "begin_combat", "attack"):
            with self.subTest(name=name):
                summary, _ = self.closing_call(name, {"character": "Bramble"})
                self.assertIn("refused", summary)
                self.assertIn("closing a scene", summary)

    def test_the_closing_tools_still_run_while_closing(self):
        # The point of the pass. Refusing these too would make a close that
        # can record nothing, which is the opposite of what it is for.
        for name in narration.CLOSING_TOOLS:
            with self.subTest(name=name):
                summary, _ = self.closing_call(name, {"character": "Bramble"})
                self.assertNotIn("closing a scene", summary)

    def open_a_fight(self, **over):
        arguments = {
            "adversaries": [
                {
                    "name": "Zombie",
                    "hit_points": 22,
                    "armour_class": 8,
                    "attack_bonus": 3,
                    "damage": "1d6+2",
                }
            ]
        }
        arguments.update(over)
        return self.call("begin_combat", arguments)

    def test_beginning_a_fight_says_who_goes_first(self):
        # Found by a real run: this used to answer "a fight began against
        # Zombie" and say nothing about the order, so the model supplied one
        # out of its own head and the report called the turn clean. Gary says
        # who is in a fight and never who goes first.
        summary, _ = self.open_a_fight()
        self.assertIn("The order is", summary)
        self.assertIn("Zombie", summary)
        self.assertIn("Bramble", summary)
        self.assertEqual(len(self.state.fight.order), 2)

    def test_a_fight_against_nothing_is_refused(self):
        summary, _ = self.open_a_fight(adversaries=[])
        self.assertIn("refused", summary)

    def test_an_attack_is_resolved_rather_than_acknowledged(self):
        # The other half of the same finding. This used to answer "Zombie
        # swung at Bramble", so the model narrated the blow missing on its
        # own authority. Whether it landed and what it cost are the two
        # things gary is never allowed to decide.
        self.open_a_fight()
        up = self.state.fight.whose
        attacker = next(
            one for one in [*self.state.party, *self.state.enemies] if one.id == up
        )
        target = "Zombie" if attacker.name == "Bramble" else "Bramble"
        summary, swing = self.call(
            "attack", {"attacker": attacker.name, "target": target}
        )
        self.assertTrue("hit" in summary or "missed" in summary, summary)
        self.assertIn("against", summary)
        self.assertIn(swing.degree, self.rules.degrees)

    def test_an_attack_out_of_turn_is_refused(self):
        self.open_a_fight()
        up = self.state.fight.whose
        waiting = next(
            one for one in [*self.state.party, *self.state.enemies] if one.id != up
        )
        other = "Zombie" if waiting.name == "Bramble" else "Bramble"
        summary, _ = self.call("attack", {"attacker": waiting.name, "target": other})
        self.assertIn("refused", summary)
        self.assertIn("not " + waiting.name + "'s turn", summary)

    def test_an_attack_with_nobody_fighting_is_refused(self):
        summary, _ = self.call("attack", {"attacker": "Bramble", "target": "x"})
        self.assertIn("refused", summary)

    def test_an_attack_on_somebody_not_in_the_fight_is_refused(self):
        self.open_a_fight()
        summary, _ = self.call("attack", {"attacker": "Bramble", "target": "the moon"})
        self.assertIn("refused", summary)

    def up(self):
        return smoke._by_id(self.state, self.state.fight.whose)

    def test_gary_may_not_end_the_players_turn_for_them(self):
        # The router refuses this: the player says what they do, and a fight
        # gary could take their turn in is one they are not playing.
        self.open_a_fight()
        # Whoever won initiative goes first, so wind the order on until it is
        # the player rather than assuming which of the two it was.
        while isinstance(self.up(), world.Foe):
            self.call("end_turn", {})
        summary, _ = self.call("end_turn", {})
        self.assertIn("refused", summary)
        self.assertIn("ask them what they do", summary)

    def test_ending_a_fight_clears_it(self):
        self.open_a_fight()
        self.call("end_combat", {})
        self.assertIsNone(self.state.fight)
        self.assertEqual(self.state.enemies, [])

    def test_a_swing_that_lands_and_one_that_does_not(self):
        # Both branches on a fixed seed, because "did it land" is the thing
        # gary is not allowed to decide and so the thing this must decide.
        # On DICE_SEED=1234 Bramble wins initiative, misses, the order wraps
        # to the zombie and back, and the third swing connects.
        self.open_a_fight()
        first, _ = self.call("attack", {"attacker": "Bramble", "target": "Zombie"})
        self.assertIn("Bramble missed Zombie", first)

        # The order wrapping is its own branch: the last fighter's turn ends
        # and the round goes up rather than the index running off the end.
        self.call("attack", {"attacker": "Zombie", "target": "Bramble"})
        self.assertEqual(self.state.fight.round, 2)

        landed, _ = self.call("attack", {"attacker": "Bramble", "target": "Zombie"})
        self.assertIn("Bramble hit Zombie for", landed)
        self.assertLess(self.state.enemies[0].hp, self.state.enemies[0].max_hp)

    def test_gary_may_end_an_adversarys_turn(self):
        # The other side of the refusal above. A fight where nobody could end
        # the zombie's turn would stop on it forever.
        self.open_a_fight()
        self.call("attack", {"attacker": "Bramble", "target": "Zombie"})
        summary, _ = self.call("end_turn", {})
        self.assertIn("Zombie's turn is over", summary)

    def test_an_adversary_that_is_not_an_object_is_skipped(self):
        # Models send odd shapes. A bare string here used to be enough to
        # stop the whole fight opening.
        summary, _ = self.open_a_fight(
            adversaries=["a zombie", {"name": "Zombie", "hit_points": 9}]
        )
        self.assertIn("The order is", summary)
        self.assertEqual(len(self.state.enemies), 1)

    def test_nobody_by_that_id(self):
        # _by_id answers None rather than raising, because the caller's next
        # line already says "nobody".
        self.assertIsNone(smoke._by_id(self.state, "not-an-id"))

    def test_ending_a_turn_with_nobody_fighting_is_refused(self):
        summary, _ = self.call("end_turn", {})
        self.assertIn("refused", summary)

    def test_a_close_writes_down_what_the_prose_added(self):
        summary, _ = self.closing_call(
            "remember", {"key": "iron-key", "value": "taken"}
        )
        self.assertEqual(self.state.facts["iron-key"], "taken")
        self.assertIn("iron-key", summary)

    def test_an_award_past_the_bound_is_refused_here_too(self):
        # The bound is the one thing about an award worth watching a real
        # model for, so this harness has to apply it rather than accept
        # anything and report a turn that the router would have refused.
        summary, _ = self.call(
            "award_experience", {"awarded": ["Bramble"], "experience": 999999}
        )
        self.assertIn("refused", summary)


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
        code, stub = run([narration.Said("The causeway.")], scene="opening")
        self.assertEqual(code, 0)

    def test_an_award_is_reported_against_the_bound(self):
        # The bound is the one thing about an award worth watching a real
        # model for, so the run says whether it was respected rather than
        # leaving it in the arguments to be checked by eye.
        code, _ = run(
            [
                narration.Calls(
                    [
                        narration.Call(
                            "award_experience",
                            {
                                "awarded": ["Bramble"],
                                "experience": 25,
                                "reason": "the mud creature",
                            },
                        )
                    ]
                ),
                narration.Said("You have earned it."),
            ],
            scene="won",
        )
        self.assertEqual(code, 0)

    def test_an_award_past_the_bound_is_reported_as_such(self):
        code, _ = run(
            [
                narration.Calls(
                    [
                        narration.Call(
                            "award_experience",
                            {
                                "awarded": ["Bramble"],
                                "experience": 999999,
                                "reason": "the prophecy",
                            },
                        )
                    ]
                ),
                narration.Said("You ascend."),
            ],
            scene="won",
        )
        # Reported, not failed: the run's job is to show what the model did,
        # and the router refusing this is the point being demonstrated.
        self.assertEqual(code, 0)

    def test_a_close_is_driven_and_its_recap_reported(self):
        code, stub = run(
            [
                narration.Calls(
                    [narration.Call("remember", {"key": "iron-key", "value": "taken"})]
                ),
                narration.Recap("They took a key and climbed out."),
            ],
            scene="close",
        )
        self.assertEqual(code, 0)
        self.assertTrue(stub.answered)

    def test_a_close_that_came_back_without_a_recap_says_so(self):
        # A scene closes either way — scenes.close_scene will not hold one
        # open for a missing paragraph — so this is reported, not failed.
        code, _ = run([narration.Recap("   ")], scene="close")
        self.assertEqual(code, 0)

    def test_a_close_reaching_outside_its_tools_is_reported(self):
        code, stub = run(
            [
                narration.Calls([narration.Call("roll", {"notation": "1d20"})]),
                narration.Recap("It ended."),
            ],
            scene="close",
        )
        self.assertEqual(code, 0)
        # Answered, and answered with a refusal rather than a number.
        self.assertIn("closing a scene", stub.answered[0][0].summary)

    def test_a_close_is_sent_the_scene_rather_than_a_player(self):
        # It has to be assembled the way scenes.close_scene assembles it, or
        # the run reports on a prompt gary never sends.
        _, stub = run(scene="close")
        self.assertEqual(stub.prompt.briefing, "")
        self.assertEqual(stub.prompt.module_hook, "")
        self.assertEqual(stub.prompt.message, "")
        self.assertEqual(stub.prompt.scene_title, smoke.SCENES["close"].title)
        self.assertEqual(stub.prompt.transcript, list(smoke.CLOSED))

    def test_the_close_scene_leaves_the_world_disagreeing_with_the_prose(self):
        # The whole point of the scene. A world that already agreed with the
        # transcript would ask a real model to reconcile nothing and then
        # report that it reconciled nothing wrong.
        state = smoke.SCENES["close"].world()
        said = " ".join(text for _, text in smoke.CLOSED)
        self.assertIn("iron key", said)
        self.assertNotIn("iron-key", state.facts)
        self.assertEqual(state.facts["bell-rings"], "3")
        self.assertIn("fourth time", said)
        self.assertIn("chamber", state.place)

    def test_the_fight_scene_starts_with_nothing_in_the_fight(self):
        # A model that wants a blow resolved has to open the fight and author
        # what is in it. Pre-loading an enemy would hand it the one thing the
        # scene exists to watch it do.
        state = smoke.SCENES["fight"].world()
        self.assertEqual(state.enemies, [])
        self.assertIsNone(state.fight)

    def test_a_fight_is_opened_and_a_blow_proposed(self):
        code, _ = run(
            [
                narration.Calls(
                    [
                        narration.Call(
                            "begin_combat",
                            {"adversaries": [{"name": "a bell-warden", "hp": 11}]},
                        )
                    ]
                ),
                narration.Calls(
                    [
                        narration.Call(
                            "attack",
                            {"attacker": "Bramble", "target": "a bell-warden"},
                        )
                    ]
                ),
                narration.Said("Steel on wet stone."),
            ],
            scene="fight",
        )
        self.assertEqual(code, 0)

    def test_a_fight_opened_against_nothing_is_named_as_such(self):
        # An empty adversary list is the shape worth catching: the model
        # asked for a fight and authored nothing to be in it.
        code, _ = run(
            [
                narration.Calls([narration.Call("begin_combat", {"adversaries": []})]),
                narration.Said("Something comes."),
            ],
            scene="fight",
        )
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

        async def fake_play(model, scene="turn"):
            seen["model"] = model
            seen["scene"] = scene
            return 0

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}, clear=True):
            with patch.object(smoke, "play", fake_play):
                with patch.object(smoke, "spend", lambda: 0.5):
                    with patch.object(smoke.sys, "argv", ["smoke", "a/named-model"]):
                        self.assertEqual(smoke.main(), 0)
        self.assertEqual(seen["model"], "a/named-model")
        self.assertEqual(seen["scene"], "turn")

    def test_falls_back_to_the_default_model(self):
        seen = {}

        async def fake_play(model, scene="turn"):
            seen["model"] = model
            return 0

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}, clear=True):
            with patch.object(smoke, "play", fake_play):
                with patch.object(smoke, "spend", lambda: None):
                    with patch.object(smoke.sys, "argv", ["smoke"]):
                        self.assertEqual(smoke.main(), 0)
        self.assertEqual(seen["model"], narration.models.default())

    def test_a_scene_can_be_asked_for_by_name(self):
        seen = {}

        async def fake_play(model, scene="turn"):
            seen["model"] = model
            seen["scene"] = scene
            return 0

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}, clear=True):
            with patch.object(smoke, "play", fake_play):
                with patch.object(smoke, "spend", lambda: None):
                    with patch.object(
                        smoke.sys, "argv", ["smoke", "--won", "a/named-model"]
                    ):
                        self.assertEqual(smoke.main(), 0)
        self.assertEqual(seen["scene"], "won")
        self.assertEqual(seen["model"], "a/named-model")

    def test_two_scenes_at_once_is_refused(self):
        # Silently taking the first would run something other than what was
        # asked for, and print a name that agreed with itself.
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}, clear=True):
            with patch.object(smoke.sys, "argv", ["smoke", "--won", "--opening"]):
                self.assertEqual(smoke.main(), 2)

    def test_every_scene_can_actually_be_played(self):
        # A scene in the table that `play` cannot build is one nobody finds
        # until they ask for it, in front of a model, having paid for it.
        for name in smoke.SCENES:
            with self.subTest(name):
                code, _ = run(scene=name)
                self.assertEqual(code, 0)

    def test_the_opening_flag_is_not_mistaken_for_a_model(self):
        # `smoke --opening` names no model, and reading the flag as one would
        # ask OpenRouter for a model called "--opening".
        seen = {}

        async def fake_play(model, scene="turn"):
            seen["model"] = model
            seen["scene"] = scene
            return 0

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}, clear=True):
            with patch.object(smoke, "play", fake_play):
                with patch.object(smoke, "spend", lambda: None):
                    with patch.object(smoke.sys, "argv", ["smoke", "--opening"]):
                        self.assertEqual(smoke.main(), 0)
        self.assertEqual(seen["model"], narration.models.default())
        self.assertEqual(seen["scene"], "opening")


if __name__ == "__main__":
    unittest.main()
