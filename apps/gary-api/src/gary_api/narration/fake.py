"""The specs' stand-in for the model.

It reads what to do straight out of the player's message, the same way
``identity.fake`` reads an identity out of the code, and for the same reason:
a scenario says what gary does at the moment it says it, so nothing has to be
arranged first and two scenarios can never leak into each other.

The directives are spec-only. They are stripped from the message before it is
stored, so a transcript never contains one, and a player who types square
brackets at a real narrator is just a player typing square brackets.

    [[roll 1d20+3 Perception]]      ask for a roll
    [[check Bramble 15 Perception]] ask the rules for a graded check
    [[move the belfry stair]]       move the party
    [[remember bell-rings=4]]       set a fact
    [[damage Bramble 4]]            take hit points off
    [[heal Bramble 2]]              put them back
    [[afflict Bramble frightened]]  add a condition
    [[time 30]]                     let time pass
    [[scene The road north]]        ask for a new scene after this turn
    [[refuse]]                      decline, in words
    [[fail]]                        be unreachable
    [[stall]]                       start, then never finish
    [[mute]]                        do the tools and never say a word

Anything else is narrated: the double echoes the message back inside a
sentence, which is enough for a spec to assert the narration mentions what
the player said without pinning prose nobody wrote.

Closing a scene is the one thing here a message cannot say, because no player
message is being answered — the scene is ending, not being played. So
``ON_CLOSE`` is arranged by a step instead, and ``environment.py`` clears it
between scenarios so it cannot leak the way message directives cannot.
"""

import re
from collections.abc import AsyncGenerator

from gary_api.narration.base import (
    Call,
    Calls,
    NarrationError,
    Prompt,
    Recap,
    Refused,
    Result,
    Said,
)

DIRECTIVE = re.compile(r"\[\[([^\]]+)\]\]")

REFUSAL = (
    "Gary would rather not narrate that. Try something else and the game "
    "carries on."
)


def directives(message: str) -> list[str]:
    return [found.strip() for found in DIRECTIVE.findall(message or "")]


def strip(message: str) -> str:
    """The message as it will be stored, with the scaffolding taken out."""
    return DIRECTIVE.sub("", message or "").strip()


def _call(directive: str) -> Call | None:
    head, _, rest = directive.partition(" ")
    rest = rest.strip()
    head = head.lower()

    if head == "roll":
        notation, _, reason = rest.partition(" ")
        return Call("roll", {"notation": notation, "reason": reason.strip()})
    if head == "check":
        character, _, tail = rest.partition(" ")
        dc, _, reason = tail.partition(" ")
        return Call(
            "check",
            {
                "character": character,
                # Left as written rather than coerced. A dc the rules cannot
                # read should reach the same refusal a model's would.
                "dc": int(dc) if dc.lstrip("-").isdigit() else dc,
                "reason": reason.strip(),
            },
        )
    if head == "move":
        return Call("move_party", {"place": rest})
    if head == "remember":
        key, _, value = rest.partition("=")
        return Call("remember", {"key": key.strip(), "value": value.strip()})
    if head in ("damage", "heal"):
        character, _, amount = rest.rpartition(" ")
        return Call(
            head,
            {
                "character": character.strip(),
                "amount": int(amount) if amount.strip().isdigit() else amount,
            },
        )
    if head in ("afflict", "relieve"):
        character, _, condition = rest.partition(" ")
        return Call(
            "add_condition" if head == "afflict" else "remove_condition",
            {"character": character, "condition": condition.strip()},
        )
    if head == "time":
        return Call(
            "pass_time", {"minutes": int(rest) if rest.isdigit() else rest}
        )
    if head == "scene":
        return Call("scene", {"title": rest})
    return None


# The last prompt this double was given, for the scenarios about what gary is
# told. Read by specs, never arranged by them — so it cannot carry anything
# from one scenario into the next beyond what the next one overwrites.
LAST: Prompt | None = None

# What the double will do when a scene closes, as directives — the same ones a
# message carries, since a close pass is the same machinery pointed at a
# different moment. Set by a step, cleared per scenario. ``None`` means the
# ordinary thing: a recap and nothing recorded.
ON_CLOSE: list[str] | None = None

# And the same for an opening, which has no player message either — the
# instruction it answers is gary-api's, not anybody's. Read once and cleared,
# so it belongs to the next narration and not to every one after it.
ON_OPEN: list[str] | None = None

# The last prompt a close pass was given, for the scenarios about which model
# was asked and what it was shown.
LAST_CLOSE: Prompt | None = None


class FakeNarrator:
    name = "fake"

    def sanitise(self, message: str) -> str:
        return strip(message)

    async def narrate(
        self, prompt: Prompt
    ) -> AsyncGenerator[Said | Calls | Refused, list[Result] | None]:
        global LAST
        LAST = prompt

        global ON_OPEN
        latest = prompt.message
        # Whatever the message carries, plus anything a scenario arranged for
        # a turn that has no message to carry it — an opening.
        asked = directives(latest) + (ON_OPEN or [])
        ON_OPEN = None

        if "fail" in asked:
            raise NarrationError("the narrator could not be reached")

        if "refuse" in asked:
            yield Refused(REFUSAL)
            return

        # Everything a real narrator does before it has said anything, and
        # nothing after. What this stands in for is the model that spends its
        # whole turn calling tools and runs out of rounds before it narrates:
        # dice thrown, hit points taken, and not one word about any of it.
        mute = "mute" in asked

        # In pieces, always. A double that answered in one go would let a
        # client that never learned to stream pass the specs.
        said = strip(latest) or "something"
        if not mute:
            yield Said("You " if said[:1].islower() else "")
            yield Said(f"{said}. ")

        calls = [call for call in (_call(one) for one in asked) if call]
        if calls:
            results = yield Calls(calls)
            for result in results or []:
                if mute:
                    continue
                if result.failed:
                    # The narrator is told what went wrong and carries on, the
                    # same way it would when a real model asks for something
                    # the rules will not do.
                    yield Said(f"That does not work: {result.summary}. ")
                else:
                    yield Said(f"{result.summary} ")

        if mute:
            return

        if "stall" in asked:
            # Started and never finished, for the scenario where the tab shuts
            # halfway. Never reaches the sentence below. Yields something
            # rather than nothing so frames keep arriving and the reader has
            # something to walk away from.
            while True:
                yield Said(" ")

        yield Said("The scene waits on you.")

    async def close(
        self, prompt: Prompt
    ) -> AsyncGenerator[Calls | Recap, list[Result] | None]:
        global LAST_CLOSE
        LAST_CLOSE = prompt

        asked = ON_CLOSE or []

        if "fail" in asked:
            raise NarrationError("the narrator could not be reached")

        calls = [call for call in (_call(one) for one in asked) if call]
        if calls:
            yield Calls(calls)

        # Built from the scene rather than invented, so a spec can assert the
        # recap is about what happened without pinning prose nobody wrote.
        said = " ".join(content for _, content in prompt.transcript if content)
        yield Recap(f"In {prompt.scene_title or 'this scene'}: {said}".strip())
