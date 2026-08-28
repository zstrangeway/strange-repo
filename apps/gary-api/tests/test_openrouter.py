"""The real narrator, against a stubbed client.

Nothing in the spec suites reaches this — they all run the double — so this
is the only thing standing between a subtly wrong streaming client and a
deploy. The fragment accumulation is the part worth the most attention: a
stub that hands over whole tool calls would agree with an implementation that
cannot handle split ones, and the split is what actually arrives.
"""

import asyncio
import json
import unittest
from unittest.mock import patch

from gary_api import narration
from gary_api.narration import openrouter
from gary_api.narration.base import Prompt


def a_prompt(model="anthropic/claude-opus-5", transcript=None):
    return Prompt(
        briefing="You are running Some Edition. Checks resolve to: success, failure.",
        model=model,
        system_slug="dnd-5e",
        module_slug="the-drowned-belfry",
        module_title="The Drowned Belfry",
        module_premise="A bell rings under the water.",
        module_hook="The reeve is paying you to stop the ringing.",
        world="Where the party is: the causeway\nThe party:\n  - Bramble",
        message="I push open the door",
        transcript=transcript or [("player", "I push open the door")],
    )


class Delta:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class ToolDelta:
    def __init__(self, index=0, name=None, arguments=None):
        self.index = index
        self.function = type(
            "Function", (), {"name": name, "arguments": arguments}
        )()


class Choice:
    def __init__(self, delta=None, finish_reason=None):
        self.delta = delta
        self.finish_reason = finish_reason


class Chunk:
    def __init__(self, choices=None, error=None):
        self.choices = choices or []
        self.error = error


class Stream:
    def __init__(self, chunks):
        self.chunks = chunks

    def __aiter__(self):
        async def go():
            for chunk in self.chunks:
                yield chunk

        return go()


def client_serving(*rounds):
    """A stubbed OpenAI client that answers each round in turn."""
    sent = []
    remaining = list(rounds)

    class Completions:
        async def create(self, **kwargs):
            sent.append(kwargs)
            if not remaining:
                raise AssertionError("asked for more rounds than were staged")
            return Stream(remaining.pop(0))

    class Chat:
        completions = Completions()

    class Client:
        chat = Chat()

    return Client(), sent


def drive(narrator, prompt, answers=None):
    """Run a narration to the end, answering tool calls from `answers`."""
    told = []

    async def go():
        generator = narrator.narrate(prompt)
        sending = None
        while True:
            try:
                event = await generator.asend(sending)
            except StopAsyncIteration:
                break
            told.append(event)
            sending = None
            if isinstance(event, narration.Calls):
                sending = [
                    narration.Result(call, (answers or {}).get(call.name, "done"))
                    for call in event.calls
                ]
        await generator.aclose()

    asyncio.run(go())
    return told


ROUNDS = openrouter.ROUNDS

# One round of a model asking for a tool and nothing else — the shape of a
# turn that never gets around to narrating.
ASKING = Chunk(
    [
        Choice(
            Delta(tool_calls=[ToolDelta(0, "pass_time", '{"minutes":1}')]),
            finish_reason="tool_calls",
        )
    ]
)


def narrator_with(client):
    made = openrouter.OpenRouterNarrator(api_key="sk-or-test", model="a/model")
    made.client = client
    return made


class StreamingTests(unittest.TestCase):
    def test_says_what_it_streams(self):
        client, _ = client_serving(
            [
                Chunk([Choice(Delta(content="The door "))]),
                Chunk([Choice(Delta(content="groans open."), finish_reason="stop")]),
            ]
        )
        told = drive(narrator_with(client), a_prompt())
        said = "".join(e.text for e in told if isinstance(e, narration.Said))
        self.assertEqual(said, "The door groans open.")

    def test_passes_the_prompt_model_rather_than_its_own(self):
        # The campaign's model wins. Two campaigns on one deployment can be on
        # different ones, so the narrator cannot be the thing that decides.
        client, sent = client_serving(
            [Chunk([Choice(Delta(content="hi"), finish_reason="stop")])]
        )
        drive(narrator_with(client), a_prompt(model="deepseek/deepseek-v3.2"))
        self.assertEqual(sent[0]["model"], "deepseek/deepseek-v3.2")

    def test_offers_every_tool_in_the_contract(self):
        client, sent = client_serving(
            [Chunk([Choice(Delta(content="hi"), finish_reason="stop")])]
        )
        drive(narrator_with(client), a_prompt())
        offered = {tool["function"]["name"] for tool in sent[0]["tools"]}
        self.assertEqual(offered, set(narration.TOOLS))

    def test_the_system_prompt_carries_the_world_and_the_module(self):
        client, sent = client_serving(
            [Chunk([Choice(Delta(content="hi"), finish_reason="stop")])]
        )
        drive(narrator_with(client), a_prompt())
        system = sent[0]["messages"][0]["content"][0]["text"]
        self.assertIn("The Drowned Belfry", system)
        self.assertIn("the causeway", system)
        self.assertIn("Some Edition", system)

    def test_the_system_prompt_asks_for_caching(self):
        client, sent = client_serving(
            [Chunk([Choice(Delta(content="hi"), finish_reason="stop")])]
        )
        drive(narrator_with(client), a_prompt())
        block = sent[0]["messages"][0]["content"][0]
        self.assertEqual(block["cache_control"], {"type": "ephemeral"})

    def test_the_transcript_becomes_alternating_turns(self):
        client, sent = client_serving(
            [Chunk([Choice(Delta(content="hi"), finish_reason="stop")])]
        )
        drive(
            narrator_with(client),
            a_prompt(transcript=[("player", "hello"), ("gm", "hi"), ("player", "again")]),
        )
        roles = [m["role"] for m in sent[0]["messages"]]
        self.assertEqual(roles, ["system", "user", "assistant", "user"])

    def test_chunks_with_no_choices_are_skipped(self):
        client, _ = client_serving(
            [
                Chunk([]),
                Chunk([Choice(Delta(content="fine"), finish_reason="stop")]),
            ]
        )
        told = drive(narrator_with(client), a_prompt())
        self.assertTrue([e for e in told if isinstance(e, narration.Said)])

    def test_a_chunk_with_no_delta_is_skipped(self):
        client, _ = client_serving(
            [
                Chunk([Choice(None)]),
                Chunk([Choice(Delta(content="fine"), finish_reason="stop")]),
            ]
        )
        told = drive(narrator_with(client), a_prompt())
        self.assertTrue([e for e in told if isinstance(e, narration.Said)])


class FragmentTests(unittest.TestCase):
    """The part a stub is most likely to agree with wrongly."""

    def test_arguments_split_across_chunks_are_reassembled(self):
        client, _ = client_serving(
            [
                Chunk([Choice(Delta(tool_calls=[ToolDelta(0, "roll", '{"nota')]))]),
                Chunk([Choice(Delta(tool_calls=[ToolDelta(0, None, 'tion": "1d')]))]),
                Chunk(
                    [
                        Choice(
                            Delta(tool_calls=[ToolDelta(0, None, '20+3"}')]),
                            finish_reason="tool_calls",
                        )
                    ]
                ),
            ],
            [Chunk([Choice(Delta(content="You find it."), finish_reason="stop")])],
        )
        told = drive(narrator_with(client), a_prompt())
        calls = [e for e in told if isinstance(e, narration.Calls)]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].calls[0].name, "roll")
        self.assertEqual(calls[0].calls[0].arguments, {"notation": "1d20+3"})

    def test_two_tools_at_once_stay_apart(self):
        client, _ = client_serving(
            [
                Chunk(
                    [
                        Choice(
                            Delta(
                                tool_calls=[
                                    ToolDelta(0, "damage", '{"character":"A",'),
                                    ToolDelta(1, "pass_time", '{"minu'),
                                ]
                            )
                        )
                    ]
                ),
                Chunk(
                    [
                        Choice(
                            Delta(
                                tool_calls=[
                                    ToolDelta(0, None, '"amount":4}'),
                                    ToolDelta(1, None, 'tes":30}'),
                                ]
                            ),
                            finish_reason="tool_calls",
                        )
                    ]
                ),
            ],
            [Chunk([Choice(Delta(content="Done."), finish_reason="stop")])],
        )
        told = drive(narrator_with(client), a_prompt())
        calls = [e for e in told if isinstance(e, narration.Calls)][0].calls
        self.assertEqual([call.name for call in calls], ["damage", "pass_time"])
        self.assertEqual(calls[0].arguments, {"character": "A", "amount": 4})
        self.assertEqual(calls[1].arguments, {"minutes": 30})

    def test_arguments_that_never_became_json_are_handed_over_empty(self):
        # Truncated mid-object. Passed on empty so the engines refuse it and
        # say why, rather than taking down a turn that is already streaming.
        client, _ = client_serving(
            [
                Chunk(
                    [
                        Choice(
                            Delta(tool_calls=[ToolDelta(0, "roll", '{"notation": "1d')]),
                            finish_reason="tool_calls",
                        )
                    ]
                ),
            ],
            [Chunk([Choice(Delta(content="Anyway."), finish_reason="stop")])],
        )
        told = drive(narrator_with(client), a_prompt())
        calls = [e for e in told if isinstance(e, narration.Calls)][0].calls
        self.assertEqual(calls[0].arguments, {})

    def test_an_opening_delta_carrying_only_the_name(self):
        # The usual shape: the name arrives first and the arguments follow in
        # later chunks.
        client, _ = client_serving(
            [
                Chunk([Choice(Delta(tool_calls=[ToolDelta(0, "pass_time", None)]))]),
                Chunk(
                    [
                        Choice(
                            Delta(tool_calls=[ToolDelta(0, None, '{"minutes":10}')]),
                            finish_reason="tool_calls",
                        )
                    ]
                ),
            ],
            [Chunk([Choice(Delta(content="Ten minutes."), finish_reason="stop")])],
        )
        told = drive(narrator_with(client), a_prompt())
        call = [e for e in told if isinstance(e, narration.Calls)][0].calls[0]
        self.assertEqual(call.name, "pass_time")
        self.assertEqual(call.arguments, {"minutes": 10})

    def test_a_delta_with_no_function_at_all_is_skipped(self):
        # An opening frame that announces an index and an id and nothing else.
        class Bare:
            def __init__(self, index):
                self.index = index

        client, _ = client_serving(
            [
                Chunk([Choice(Delta(tool_calls=[Bare(0)]))]),
                Chunk(
                    [
                        Choice(
                            Delta(
                                tool_calls=[ToolDelta(0, "pass_time", '{"minutes":5}')]
                            ),
                            finish_reason="tool_calls",
                        )
                    ]
                ),
            ],
            [Chunk([Choice(Delta(content="Five."), finish_reason="stop")])],
        )
        told = drive(narrator_with(client), a_prompt())
        call = [e for e in told if isinstance(e, narration.Calls)][0].calls[0]
        self.assertEqual(call.arguments, {"minutes": 5})

    def test_a_nameless_index_beside_a_named_one_is_dropped(self):
        client, _ = client_serving(
            [
                Chunk(
                    [
                        Choice(
                            Delta(
                                tool_calls=[
                                    ToolDelta(0, "pass_time", '{"minutes":5}'),
                                    ToolDelta(1, None, '{"orphan":true}'),
                                ]
                            ),
                            finish_reason="tool_calls",
                        )
                    ]
                ),
            ],
            [Chunk([Choice(Delta(content="Five."), finish_reason="stop")])],
        )
        told = drive(narrator_with(client), a_prompt())
        calls = [e for e in told if isinstance(e, narration.Calls)][0].calls
        self.assertEqual([call.name for call in calls], ["pass_time"])

    def test_a_fragment_with_no_name_is_not_a_call(self):
        client, _ = client_serving(
            [
                Chunk(
                    [
                        Choice(
                            Delta(tool_calls=[ToolDelta(0, None, "{}")]),
                            finish_reason="stop",
                        )
                    ]
                ),
            ]
        )
        told = drive(narrator_with(client), a_prompt())
        self.assertFalse([e for e in told if isinstance(e, narration.Calls)])

    def test_results_go_back_as_tool_messages(self):
        client, sent = client_serving(
            [
                Chunk(
                    [
                        Choice(
                            Delta(tool_calls=[ToolDelta(0, "roll", '{"notation":"1d20"}')]),
                            finish_reason="tool_calls",
                        )
                    ]
                ),
            ],
            [Chunk([Choice(Delta(content="A seventeen."), finish_reason="stop")])],
        )
        drive(narrator_with(client), a_prompt(), answers={"roll": "1d20 came up 17"})
        second = sent[1]["messages"]
        self.assertEqual(second[-1]["role"], "tool")
        self.assertIn("came up 17", second[-1]["content"])
        self.assertEqual(second[-2]["role"], "assistant")
        self.assertEqual(
            json.loads(second[-2]["tool_calls"][0]["function"]["arguments"]),
            {"notation": "1d20"},
        )

    def test_a_refused_tool_is_reported_as_refused(self):
        client, sent = client_serving(
            [
                Chunk(
                    [
                        Choice(
                            Delta(tool_calls=[ToolDelta(0, "roll", '{"notation":"bad"}')]),
                            finish_reason="tool_calls",
                        )
                    ]
                ),
            ],
            [Chunk([Choice(Delta(content="Never mind."), finish_reason="stop")])],
        )

        async def go():
            narrator = narrator_with(client)
            generator = narrator.narrate(a_prompt())
            sending = None
            while True:
                try:
                    event = await generator.asend(sending)
                except StopAsyncIteration:
                    break
                sending = None
                if isinstance(event, narration.Calls):
                    sending = [
                        narration.Result(call, "gary cannot roll that", failed=True)
                        for call in event.calls
                    ]
            await generator.aclose()

        asyncio.run(go())
        self.assertIn("refused:", sent[1]["messages"][-1]["content"])


class FailureTests(unittest.TestCase):
    def test_an_error_frame_mid_stream_is_a_narration_error(self):
        # HTTP is still 200 — the headers went out long ago — so the failure
        # arrives as content and has to be recognised as one.
        client, _ = client_serving(
            [
                Chunk([Choice(Delta(content="The door "))]),
                Chunk(error={"code": 502, "message": "upstream fell over"}),
            ]
        )
        with self.assertRaises(narration.NarrationError):
            drive(narrator_with(client), a_prompt())

    def test_finish_reason_error_is_a_narration_error(self):
        client, _ = client_serving(
            [Chunk([Choice(Delta(content="half a "), finish_reason="error")])]
        )
        with self.assertRaises(narration.NarrationError):
            drive(narrator_with(client), a_prompt())

    def test_the_client_falling_over_is_a_narration_error(self):
        class Exploding:
            class chat:
                class completions:
                    @staticmethod
                    async def create(**kwargs):
                        raise RuntimeError("no route to host")

        with self.assertRaises(narration.NarrationError):
            drive(narrator_with(Exploding()), a_prompt())

    def test_a_model_that_asks_forever_is_stopped(self):
        # Otherwise one confused turn spends the account. It is an error
        # rather than a quiet stop: a model still calling tools on the round
        # that forbade them has lost the thread, and the player is owed an
        # answer rather than a turn that simply ends.
        client, sent = client_serving(*[[ASKING] for _ in range(ROUNDS + 5)])
        with self.assertRaises(narration.NarrationError):
            drive(narrator_with(client), a_prompt())
        self.assertEqual(len(sent), ROUNDS)


class WrappingUpTests(unittest.TestCase):
    """What happens when gary runs out of room to keep asking.

    Reported from a real session: seven rolls landed and gary never narrated
    a word. It had spent every round calling tools — a party of four crossing
    one hazard, asked for one at a time — and the loop fell out of the bottom
    having said nothing, which reads as the app freezing rather than as a
    turn ending.
    """

    def test_the_last_round_forbids_tools_and_asks_for_prose(self):
        client, sent = client_serving(
            *[[ASKING] for _ in range(ROUNDS - 1)],
            [Chunk([Choice(Delta(content="The planks give."), finish_reason="stop")])],
        )
        drive(narrator_with(client), a_prompt())

        self.assertEqual(len(sent), ROUNDS)
        # Every round but the last may ask for whatever it needs.
        for asked in sent[:-1]:
            self.assertEqual(asked["tool_choice"], "auto")

        last = sent[-1]
        self.assertEqual(last["tool_choice"], "none")
        # Described but forbidden, rather than withdrawn: the conversation is
        # full of calls to them by now.
        self.assertTrue(last["tools"])
        self.assertIn(
            openrouter.WRAP_UP,
            [
                message.get("content")
                for message in last["messages"]
                if message.get("role") == "user"
            ],
        )

    def test_a_turn_that_used_every_round_still_ends_in_prose(self):
        client, _ = client_serving(
            *[[ASKING] for _ in range(ROUNDS - 1)],
            [Chunk([Choice(Delta(content="You are all in the water."), finish_reason="stop")])],
        )
        told = drive(narrator_with(client), a_prompt())

        said = "".join(e.text for e in told if isinstance(e, narration.Said))
        self.assertEqual(said, "You are all in the water.")

    def test_an_ordinary_turn_never_forbids_tools(self):
        client, sent = client_serving(
            [Chunk([Choice(Delta(content="The door groans."), finish_reason="stop")])]
        )
        drive(narrator_with(client), a_prompt())

        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["tool_choice"], "auto")
        self.assertNotIn(
            openrouter.WRAP_UP,
            [message.get("content") for message in sent[0]["messages"]],
        )


class SelectionTests(unittest.TestCase):
    def setUp(self):
        narration.narrator.cache_clear()

    def tearDown(self):
        narration.narrator.cache_clear()

    def test_a_real_narrator_is_built_when_there_is_a_key(self):
        with patch.dict(
            "os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}, clear=True
        ):
            built = narration.narrator("deepseek/deepseek-v3.2")
        self.assertIsInstance(built, openrouter.OpenRouterNarrator)
        self.assertEqual(built.model, "deepseek/deepseek-v3.2")

    def test_one_per_model_rather_than_one_per_process(self):
        with patch.dict(
            "os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}, clear=True
        ):
            first = narration.narrator("a/one")
            again = narration.narrator("a/one")
            other = narration.narrator("b/two")
        self.assertIs(first, again)
        self.assertIsNot(first, other)

    def test_it_reports_itself_configured(self):
        with patch.dict(
            "os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}, clear=True
        ):
            narration.report_configuration()

    def test_a_real_narrator_takes_a_message_as_it_is(self):
        with patch.dict(
            "os.environ", {"OPENROUTER_API_KEY": "sk-or-test"}, clear=True
        ):
            built = narration.narrator("a/one")
        said = "I search the room [[not a directive]]"
        self.assertEqual(built.sanitise(said), said)


if __name__ == "__main__":
    unittest.main()


def close_with(narrator, prompt, answers=None):
    """Run a close pass to the end, answering tool calls from `answers`."""
    told = []

    async def go():
        generator = narrator.close(prompt)
        sending = None
        while True:
            try:
                event = await generator.asend(sending)
            except StopAsyncIteration:
                break
            told.append(event)
            sending = None
            if isinstance(event, narration.Calls):
                sending = [
                    narration.Result(call, (answers or {}).get(call.name, "done"))
                    for call in event.calls
                ]
        await generator.aclose()

    asyncio.run(go())
    return told


class ClosingTests(unittest.TestCase):
    """The close pass — unreachable from the specs, like everything here."""

    def test_sums_up_what_it_was_shown(self):
        client, _ = client_serving(
            [
                Chunk([Choice(Delta(content="The party "))]),
                Chunk([Choice(Delta(content="opened the door."), finish_reason="stop")]),
            ]
        )
        told = close_with(narrator_with(client), a_prompt())
        self.assertEqual(len(told), 1)
        self.assertIsInstance(told[0], narration.Recap)
        self.assertEqual(told[0].text, "The party opened the door.")

    def test_offers_only_the_closing_tools(self):
        # A die thrown after the scene is over would decide something nobody
        # was at the table for, so `roll` and `check` are not on offer.
        client, sent = client_serving(
            [Chunk([Choice(Delta(content="done"), finish_reason="stop")])]
        )
        close_with(narrator_with(client), a_prompt())
        offered = {tool["function"]["name"] for tool in sent[0]["tools"]}
        self.assertEqual(offered, set(narration.CLOSING_TOOLS))
        self.assertNotIn("roll", offered)
        self.assertNotIn("scene", offered)

    def test_records_before_it_sums_up(self):
        client, sent = client_serving(
            [
                Chunk(
                    [
                        Choice(
                            Delta(
                                tool_calls=[
                                    ToolDelta(0, "remember", '{"key": "brass-key",'),
                                    ToolDelta(0, None, ' "value": "pocketed"}'),
                                ]
                            ),
                            finish_reason="tool_calls",
                        )
                    ]
                ),
                Chunk([Choice(Delta(content="A key was found."), finish_reason="stop")]),
            ],
            [Chunk([Choice(Delta(content="A key was found."), finish_reason="stop")])],
        )
        told = close_with(narrator_with(client), a_prompt())

        calls = [e for e in told if isinstance(e, narration.Calls)]
        self.assertEqual(calls[0].calls[0].name, "remember")
        self.assertEqual(
            calls[0].calls[0].arguments, {"key": "brass-key", "value": "pocketed"}
        )
        self.assertEqual(told[-1].text, "A key was found.")
        # What the tools came back with goes in before it writes the recap.
        self.assertEqual(sent[1]["messages"][-1]["role"], "tool")

    def test_a_refused_tool_is_told_it_was_refused(self):
        client, sent = client_serving(
            [
                Chunk(
                    [
                        Choice(
                            Delta(
                                tool_calls=[
                                    ToolDelta(0, "damage", '{"character": "Nobody"}')
                                ]
                            ),
                            finish_reason="tool_calls",
                        )
                    ]
                ),
            ],
            [Chunk([Choice(Delta(content="Nothing happened."), finish_reason="stop")])],
        )

        told = []

        async def go():
            generator = narrator_with(client).close(a_prompt())
            sending = None
            while True:
                try:
                    event = await generator.asend(sending)
                except StopAsyncIteration:
                    break
                told.append(event)
                sending = None
                if isinstance(event, narration.Calls):
                    sending = [
                        narration.Result(call, "nobody here is called Nobody", failed=True)
                        for call in event.calls
                    ]
            await generator.aclose()

        asyncio.run(go())
        self.assertTrue(sent[1]["messages"][-1]["content"].startswith("refused:"))

    def test_asks_for_the_scene_model_it_was_given(self):
        client, sent = client_serving(
            [Chunk([Choice(Delta(content="done"), finish_reason="stop")])]
        )
        close_with(
            narrator_with(client), a_prompt(model="anthropic/claude-haiku-4.5")
        )
        self.assertEqual(sent[0]["model"], "anthropic/claude-haiku-4.5")

    def test_shows_it_the_scene_it_is_closing(self):
        client, sent = client_serving(
            [Chunk([Choice(Delta(content="done"), finish_reason="stop")])]
        )
        close_with(
            narrator_with(client),
            a_prompt(transcript=[("player", "I push the door"), ("gm", "It gives.")]),
        )
        shown = sent[0]["messages"][1]["content"]
        self.assertIn("I push the door", shown)
        self.assertIn("It gives.", shown)

    def test_a_scene_with_nothing_said_in_it_still_asks(self):
        # scenes.py does not call this for an empty scene, but nothing here
        # may assume that: an empty transcript must not produce an empty user
        # message, which some providers reject outright.
        client, sent = client_serving(
            [Chunk([Choice(Delta(content="done"), finish_reason="stop")])]
        )
        close_with(narrator_with(client), a_prompt(transcript=[]))
        self.assertTrue(sent[0]["messages"][1]["content"].strip())

    def test_a_mid_stream_error_is_a_narration_error(self):
        client, _ = client_serving([Chunk(error={"message": "upstream fell over"})])
        with self.assertRaises(narration.NarrationError):
            close_with(narrator_with(client), a_prompt())

    def test_empty_chunks_are_skipped_rather_than_ending_the_recap(self):
        # Both shapes really arrive: a chunk with no choices at all, and one
        # whose choice carries no delta. Reading either as the end would cut
        # a recap off partway.
        client, _ = client_serving(
            [
                Chunk([]),
                Chunk([Choice(None)]),
                Chunk([Choice(Delta(content="They crossed."), finish_reason="stop")]),
            ]
        )
        told = close_with(narrator_with(client), a_prompt())
        self.assertEqual(told[-1].text, "They crossed.")

    def test_a_transport_failure_is_a_narration_error(self):
        class Exploding:
            class chat:
                class completions:
                    @staticmethod
                    async def create(**kwargs):
                        raise RuntimeError("connection reset")

        with self.assertRaises(narration.NarrationError):
            close_with(narrator_with(Exploding()), a_prompt())

    def test_gives_up_rather_than_asking_forever(self):
        # Better an empty recap than a scene that will not close.
        asking = [
            Chunk(
                [
                    Choice(
                        Delta(tool_calls=[ToolDelta(0, "pass_time", '{"minutes": 1}')]),
                        finish_reason="tool_calls",
                    )
                ]
            )
        ]
        client, _ = client_serving(asking, asking, asking, asking)
        told = close_with(narrator_with(client), a_prompt())
        self.assertEqual(told[-1].text, "")


class WhatGaryIsToldToDoTests(unittest.TestCase):
    """Awarding needs a rule in the prompt, not just a tool description.

    Found by a real smoke run: handed a scene where a monster had just been
    killed, the model narrated the aftermath, called nothing at all, and
    `award_experience` went untouched. Most tools are self-evident from what
    they do — `attack`, `heal`, `end_combat` — and a model reaches for them
    when the fiction calls for one. Awarding is not: nothing in a turn says
    "and now hand out experience" unless gary has been told that overcoming
    something is when you do it.
    """

    def test_gary_is_told_to_award_experience(self):
        text = openrouter.system_prompt(a_prompt())
        self.assertIn("award experience", text)

    def test_gary_is_told_the_level_is_not_its_to_give(self):
        text = openrouter.system_prompt(a_prompt())
        self.assertIn("never say what level", text)


class LongMemoryTests(unittest.TestCase):
    def test_says_plainly_when_there_is_nothing_before_this_scene(self):
        text = openrouter.system_prompt(a_prompt())
        self.assertIn("first scene", text)

    def test_carries_the_recaps_and_says_the_prose_is_gone(self):
        prompt = a_prompt()
        prompt.recaps = [("The causeway", "They crossed at dusk.")]
        prompt.scene_title = "The flooded nave"
        text = openrouter.system_prompt(prompt)

        self.assertIn("They crossed at dusk.", text)
        self.assertIn("The causeway", text)
        self.assertIn("The flooded nave", text)
        # A model that thinks it merely was not sent the detail will write as
        # though it could ask for it.
        self.assertIn("gone", text)

    def test_an_untitled_earlier_scene_is_still_shown(self):
        prompt = a_prompt()
        prompt.recaps = [("", "Something happened.")]
        text = openrouter.system_prompt(prompt)
        self.assertIn("Something happened.", text)
        self.assertIn("Untitled", text)


class HookTests(unittest.TestCase):
    """Why the party is here — the question gary kept handing back."""

    def test_the_hook_reaches_the_model(self):
        text = openrouter.system_prompt(a_prompt())
        self.assertIn("The reeve is paying you", text)

    def test_a_module_with_no_hook_says_so_rather_than_nothing(self):
        # Silence would read as "no reason exists"; this reads as "nobody has
        # told you", which is the truth and is actable on.
        prompt = a_prompt()
        prompt.module_hook = ""
        self.assertIn("Nobody has said why", openrouter.system_prompt(prompt))

    def test_it_is_told_never_to_hand_the_question_back(self):
        # The exact failure this exists to stop: asked "why am I here", gary
        # answered "perhaps you have your own reasons".
        text = openrouter.system_prompt(a_prompt())
        self.assertIn("your own reasons", text)
