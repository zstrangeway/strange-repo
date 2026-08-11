"""The real narrator, through OpenRouter.

OpenRouter serves an OpenAI-compatible ``/api/v1/chat/completions`` and no
Anthropic ``/v1/messages``, so this is the ``openai`` client pointed at a
different base url — even when the model on the other end is a Claude. What
that costs us is written down in the plan; the short version is that there
are no typed refusals here, so a model declining arrives as ordinary prose.

Two shapes are easy to get wrong and are the reason this file exists rather
than a few lines inline:

**Tool calls arrive in fragments.** A streamed ``tool_calls`` delta carries an
index, sometimes an id and a name, and a slice of the arguments JSON. The
slices have to be accumulated per index before anything can parse them —
``{"notation": "1d2`` is not JSON and never will be until the next chunk.

**Errors arrive as content, not as status.** Once OpenRouter has sent headers
it cannot change its mind, so a mid-stream failure is a frame with ``error``
at the top level and HTTP still 200. That is exactly the shape gary's own
stream uses, which is a happy accident of having built the stream first.
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI

from gary_api import logs
from gary_api.narration.base import (
    CLOSING_TOOLS,
    TOOLS,
    Calls,
    Call,
    NarrationError,
    Prompt,
    Recap,
    Refused,
    Result,
    Said,
)

logger = logs.get_logger(__name__)

BASE_URL = "https://openrouter.ai/api/v1"

# Sent so gary shows up as itself in OpenRouter's dashboards rather than as an
# anonymous key.
HEADERS = {
    "HTTP-Referer": "https://github.com/zstrangeway/strange-repo",
    "X-Title": "gary",
}

# Enough for a scene and its tool calls. A turn that wants more than this is
# a turn that has gone wrong.
MAX_TOKENS = 4096

# How hard to think. Latency is felt directly in a chat window, so this starts
# in the middle rather than at the top and is worth sweeping once there are
# real turns to compare.
EFFORT = "medium"

# How many times gary may go back for more before it has to say something.
#
# Each one is a whole request carrying the conversation so far, so this is a
# ceiling on both the cost and the wait of a single turn, not a free dial.
# Eight was too few: a party of four crossing one hazard is four checks and
# the damage that follows, and a model that asks for them one at a time —
# which they do — reaches the wall describing a single moment.
#
# The last of these is spent narrating rather than asking, so the number of
# rounds gary can actually call tools in is one less than this.
ROUNDS = 15

# What gary is told on the round it has to finish in. Stated as the situation
# rather than as a scolding: a model told it has failed tends to apologise to
# the player, who never asked and cannot help.
WRAP_UP = (
    "That is all the time you have for looking things up this turn. Do not "
    "call any more tools. Say what happened, using what you already have."
)

# What every tool takes, in the shape OpenAI-compatible APIs want. Built from
# narration.TOOLS so a tool that exists in the contract cannot be missing from
# what the model is offered.
NUMBERS = {"dc", "modifier", "amount", "minutes"}


def schema(offered: tuple[str, ...] | None = None) -> list[dict]:
    """The tools, in the shape OpenAI-compatible APIs want.

    Takes which ones rather than always all of them, because the close pass
    is offered a subset — see ``narration.CLOSING_TOOLS``. A tool nobody can
    usefully call at a given moment is better withheld than described and
    then refused.
    """
    described = {
        "notation": "Dice to roll, as NdM+K — for example 1d20+3.",
        "reason": "What the roll or check is for, in a word or two.",
        "character": "The name of the character it applies to.",
        "dc": "The difficulty class to beat.",
        "modifier": "The character's modifier for this check.",
        "place": "Where the party now is.",
        "key": "A short name for the fact.",
        "value": "What the fact says.",
        "amount": "How many hit points.",
        "condition": "The condition, in one word.",
        "minutes": "How many minutes passed.",
        "title": "A short name for the scene beginning.",
    }
    purpose = {
        "roll": "Roll dice. You never invent a number yourself — call this.",
        "check": (
            "Make a check against a difficulty. The rules grade it and tell "
            "you the degree of success; you never decide that yourself."
        ),
        "move_party": "Record that the party has moved somewhere new.",
        "remember": "Record a fact about the world so it is still true later.",
        "damage": "Take hit points off a character.",
        "heal": "Give hit points back to a character.",
        "add_condition": "Record that a character is under a condition.",
        "remove_condition": "Record that a condition has ended.",
        "pass_time": "Record that time has passed.",
        "scene": (
            "Begin a new scene once this turn is over. Call this when the "
            "story moves somewhere else, or time skips, or a chapter ends."
        ),
    }

    built = []
    for name, fields in TOOLS.items():
        if offered is not None and name not in offered:
            continue
        properties = {
            field: {
                "type": "integer" if field in NUMBERS else "string",
                "description": described[field],
            }
            for field in fields
        }
        built.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": purpose[name],
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        # Only what a call cannot do without. A modifier the
                        # model has no view on should be omitted rather than
                        # invented to satisfy a schema.
                        "required": [
                            field for field in fields if field != "modifier"
                        ],
                    },
                },
            }
        )
    return built


def system_prompt(prompt: Prompt) -> str:
    """Everything gary is told about the game it is running.

    Assembled from the ruleset and the world rather than written out per
    system, so a new system arrives already able to describe itself and this
    function never learns a name.
    """
    return "\n\n".join(
        [
            "You are Gary, a game master running a tabletop roleplaying game.",
            prompt.briefing,
            f"The module is {prompt.module_title}.\n\n{prompt.module_premise}",
            (
                "Why the party is here:\n" + prompt.module_hook
                if prompt.module_hook
                else "Nobody has said why the party is here."
            ),
            _so_far(prompt),
            "The world as it currently stands:\n" + prompt.world,
            (
                "Rules you follow without exception:\n"
                "- You never invent a die roll or decide how well a check "
                "went. Call the tools and narrate what they return.\n"
                "- You never state that the world changed without recording "
                "it. Moving the party, hurting someone, establishing a fact — "
                "each has a tool, and the tool is what makes it true.\n"
                "- The world above is what is true. Do not contradict it, and "
                "that includes counts, names, places and elapsed time. If the "
                "world says the bell has rung three times, it has rung three "
                "times; narrating a fourth without calling `remember` first "
                "makes your own story wrong on the next turn, because the "
                "world is what you will be told then and your prose is not.\n"
                "- If a tool refuses, that refusal is what happened. Narrate "
                "around it rather than pretending it worked."
            ),
            (
                "What is yours and what is theirs. The world is yours: what "
                "is happening, who wants what, why the party was sent, what "
                "everything that is not their character does about it. Their "
                "character's choices are theirs alone. So when a player asks "
                "why they are here, or who hired them, or what they know — "
                "answer it from what you were told above. Do not hand the "
                "question back and do not invite them to make it up. 'Perhaps "
                "you have your own reasons' is the one thing you may never "
                "say."
            ),
            (
                "Keep the prose tight — a paragraph or two, ending somewhere "
                "the player can act. Address the player as 'you'. Do not "
                "write their character's decisions for them."
            ),
        ]
    )


def _so_far(prompt: Prompt) -> str:
    """The campaign before this scene, at a few sentences a scene.

    What is below is all gary has of those scenes — the turns themselves are
    out of context and are not coming back. Said plainly here, because a model
    that thinks it merely was not sent the detail will write as though it
    could ask for it.
    """
    if not prompt.recaps:
        return (
            "This is the first scene of the campaign. Nothing has happened "
            "yet beyond what the module says."
        )

    lines = [
        "Earlier scenes, in the only form you still have them. The prose of "
        "those scenes is gone; these summaries and the world state below are "
        "what is left, and they are enough — do not write as though you can "
        "recall more."
    ]
    for index, (title, recap) in enumerate(prompt.recaps, start=1):
        lines.append(f"{index}. {title or 'Untitled'} — {recap}")

    if prompt.scene_title:
        lines.append(f"The scene now being played is called {prompt.scene_title}.")

    return "\n".join(lines)


def closing_prompt(prompt: Prompt) -> str:
    """What gary is told when a scene ends.

    Two jobs, and the order matters: record first, sum up second. The
    recording is the part with a deadline — after this the transcript is gone
    and a fact nobody wrote down cannot be recovered — while the summary is
    merely useful.
    """
    return "\n\n".join(
        [
            (
                "You are Gary, and a scene of the game you are running has "
                "just ended. You are not narrating now. You have two jobs."
            ),
            "The world as it currently stands:\n" + prompt.world,
            (
                "First: read the scene below and look for anything you "
                "narrated that the world does not know about — somewhere the "
                "party ended up, an injury, a fact established, time that "
                "passed. Record each one with the matching tool. This is your "
                "last chance to: the scene is about to leave your memory, and "
                "what is not recorded now is lost. Record only what the scene "
                "actually shows. Do not invent, and do not record something "
                "the world already has."
            ),
            (
                "Second: write a short recap of the scene — three or four "
                "sentences, past tense, covering what changed and what is "
                "unresolved. This is all you will be told about this scene "
                "from now on, so write it for a reader who has forgotten "
                "everything else."
            ),
        ]
    )


def messages(prompt: Prompt) -> list[dict]:
    built: list[dict] = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": system_prompt(prompt),
                    # Passthrough to Anthropic-family models. OpenRouter
                    # documents a 4096-token floor for Opus, well above
                    # Anthropic's own — so a short preamble silently will not
                    # cache. Worth measuring rather than claiming.
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        }
    ]

    for role, content in prompt.transcript:
        built.append(
            {"role": "user" if role == "player" else "assistant", "content": content}
        )

    return built


class Fragments:
    """Tool calls as they arrive, in pieces.

    A streamed delta carries an index and a slice of the arguments JSON. Only
    once the stream stops asking is any of it parseable, so everything is kept
    by index until then.
    """

    def __init__(self) -> None:
        self.by_index: dict[int, dict[str, Any]] = {}

    def add(self, deltas) -> None:
        for delta in deltas or []:
            at = getattr(delta, "index", 0) or 0
            held = self.by_index.setdefault(at, {"name": "", "arguments": ""})
            function = getattr(delta, "function", None)
            if function is None:
                continue
            if getattr(function, "name", None):
                held["name"] = function.name
            if getattr(function, "arguments", None):
                held["arguments"] += function.arguments

    def calls(self) -> list[Call]:
        built = []
        for _, held in sorted(self.by_index.items()):
            if not held["name"]:
                continue
            raw = held["arguments"].strip() or "{}"
            try:
                arguments = json.loads(raw)
            except json.JSONDecodeError:
                # A truncated or malformed argument list. Passed on as empty
                # so the engines refuse it and say why, rather than crashing
                # a turn that is already streaming.
                logger.warning(
                    "gm.unparseable_arguments", tool=held["name"], raw=raw[:200]
                )
                arguments = {}
            built.append(Call(held["name"], arguments if isinstance(arguments, dict) else {}))
        return built

    def __bool__(self) -> bool:
        return any(held["name"] for held in self.by_index.values())


class OpenRouterNarrator:
    name = "openrouter"

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key, base_url=BASE_URL, default_headers=HEADERS
        )

    def sanitise(self, message: str) -> str:
        # Nothing to take out. A player typing square brackets at a real
        # narrator is just a player typing square brackets.
        return message

    async def narrate(
        self, prompt: Prompt
    ) -> AsyncGenerator[Said | Calls | Refused, list[Result] | None]:
        conversation = messages(prompt)

        # Rounds, not one pass: a tool call ends a completion, and what the
        # tools came back with has to go in before the model can carry on.
        for round_ in range(ROUNDS):
            # The last one is spent saying what happened. Reaching the cap
            # used to end the turn in silence — the loop fell out of the
            # bottom having narrated nothing — which read to the player as
            # gary freezing mid-sentence. A turn always ends in prose now,
            # even when gary has run out of room to keep asking.
            last = round_ == ROUNDS - 1
            if last:
                logger.warning(
                    "gm.out_of_rounds", model=prompt.model or self.model
                )
                conversation.append({"role": "user", "content": WRAP_UP})

            fragments = Fragments()
            spoken: list[str] = []
            finish = None

            try:
                stream = await self.client.chat.completions.create(
                    model=prompt.model or self.model,
                    messages=conversation,
                    tools=schema(),
                    # Left described rather than withdrawn: the conversation
                    # above is full of calls to them, and taking the
                    # definitions away mid-thread reads as a contradiction.
                    tool_choice="none" if last else "auto",
                    max_tokens=MAX_TOKENS,
                    stream=True,
                    extra_body={"reasoning": {"effort": EFFORT}},
                )

                async for chunk in stream:
                    # A mid-stream failure arrives as a frame rather than a
                    # status, because the headers went out long ago.
                    problem = getattr(chunk, "error", None)
                    if problem:
                        raise NarrationError(str(problem))

                    if not chunk.choices:
                        continue

                    choice = chunk.choices[0]
                    finish = choice.finish_reason or finish
                    delta = choice.delta
                    if delta is None:
                        continue

                    if delta.content:
                        spoken.append(delta.content)
                        yield Said(delta.content)

                    fragments.add(getattr(delta, "tool_calls", None))

            except NarrationError:
                raise
            except Exception as error:
                raise NarrationError(str(error)) from error

            if finish == "error":
                raise NarrationError("the model stopped partway")

            if not fragments:
                return

            calls = fragments.calls()
            conversation.append(
                {
                    "role": "assistant",
                    "content": "".join(spoken),
                    "tool_calls": [
                        {
                            "id": f"call_{index}",
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(call.arguments),
                            },
                        }
                        for index, call in enumerate(calls)
                    ],
                }
            )

            results = yield Calls(calls)
            for index, result in enumerate(results or []):
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": f"call_{index}",
                        "content": (
                            f"refused: {result.summary}"
                            if result.failed
                            else result.summary
                        ),
                    }
                )

        # Only reachable if a model kept calling tools through a round that
        # forbade them. Raised rather than logged and swallowed: the player is
        # owed an answer, and silence is the one thing that reads as the app
        # being broken rather than gary having a bad night.
        raise NarrationError("gary lost the thread of that turn")

    async def close(
        self, prompt: Prompt
    ) -> AsyncGenerator[Calls | Recap, list[Result] | None]:
        conversation: list[dict] = [
            {"role": "system", "content": closing_prompt(prompt)},
            {
                "role": "user",
                "content": "The scene that just ended:\n\n"
                + (
                    "\n\n".join(
                        f"{'Player' if role == 'player' else 'Gary'}: {content}"
                        for role, content in prompt.transcript
                        if content
                    )
                    or "Nothing was said."
                ),
            },
        ]

        # Fewer rounds than narrating gets. Reconciling a scene is a bounded
        # job — read it once, record what is missing, sum it up — and a close
        # pass still asking on the fourth round has stopped doing that.
        for _ in range(4):
            fragments = Fragments()
            spoken: list[str] = []

            try:
                stream = await self.client.chat.completions.create(
                    model=prompt.model or self.model,
                    messages=conversation,
                    tools=schema(CLOSING_TOOLS),
                    max_tokens=MAX_TOKENS,
                    stream=True,
                )

                async for chunk in stream:
                    problem = getattr(chunk, "error", None)
                    if problem:
                        raise NarrationError(str(problem))
                    if not chunk.choices:
                        continue

                    delta = chunk.choices[0].delta
                    if delta is None:
                        continue
                    if delta.content:
                        spoken.append(delta.content)
                    fragments.add(getattr(delta, "tool_calls", None))

            except NarrationError:
                raise
            except Exception as error:
                raise NarrationError(str(error)) from error

            if not fragments:
                # Nothing more to record, so what it wrote is the recap.
                yield Recap("".join(spoken).strip())
                return

            calls = fragments.calls()
            conversation.append(
                {
                    "role": "assistant",
                    "content": "".join(spoken),
                    "tool_calls": [
                        {
                            "id": f"call_{index}",
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(call.arguments),
                            },
                        }
                        for index, call in enumerate(calls)
                    ],
                }
            )

            results = yield Calls(calls)
            for index, result in enumerate(results or []):
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": f"call_{index}",
                        "content": (
                            f"refused: {result.summary}"
                            if result.failed
                            else result.summary
                        ),
                    }
                )

        # Out of rounds with nothing written. Better an empty recap than a
        # scene that will not close.
        logger.warning("gm.close_too_many_rounds", model=prompt.model or self.model)
        yield Recap("")
