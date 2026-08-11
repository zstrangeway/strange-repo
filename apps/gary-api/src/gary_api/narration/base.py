"""What gary asks of a narrator, and what a narrator may ask back.

The narrator is the only part of gary that is not deterministic, so it is
also the only part that is not trusted with anything. It proposes: a roll, a
check, a change to the world. Something else decides what those come to and
writes them down. What comes back to the narrator is what actually happened,
which it then describes.

That is why ``narrate`` is a two-way generator rather than a function that
returns prose. The caller drives it: every time it yields a ``Calls`` the
caller runs the tools, and sends the results back in. The engines stay in the
router where the database is, and no narrator — real or stood in — can reach
them.

Nothing here knows which system is running. The briefing is a string the
ruleset produced about itself.
"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Protocol


class NarrationError(Exception):
    """The narrator could not be reached, or answered with nothing usable."""


# The tools a narrator may call. Names and shapes live here so that the double
# and the real thing cannot drift: a tool the spec exercises but the model is
# never offered is a tool that does not exist.
TOOLS = {
    "roll": ("notation", "reason"),
    "check": ("character", "dc", "reason"),
    "move_party": ("place",),
    "remember": ("key", "value"),
    "damage": ("character", "amount"),
    "heal": ("character", "amount"),
    "add_condition": ("character", "condition"),
    "remove_condition": ("character", "condition"),
    "pass_time": ("minutes",),
    "scene": ("title",),
}

# What the close pass may call. A recap does not roll dice and does not grade
# a check — it is looking back at what was already decided, and a die thrown
# after the fact would decide something nobody was there for. Everything left
# is a change to the world, which is the whole business of reconciling.
CLOSING_TOOLS = tuple(
    name for name in TOOLS if name not in ("roll", "check", "scene")
)


@dataclass(frozen=True)
class Said:
    """A piece of prose, as it is generated."""

    text: str


@dataclass(frozen=True)
class Call:
    name: str
    arguments: dict


@dataclass(frozen=True)
class Calls:
    """One or more tools the narrator wants run before it goes on."""

    calls: list[Call]


@dataclass(frozen=True)
class Refused:
    """The narrator declined, and said why in words a player can read."""

    detail: str


@dataclass(frozen=True)
class Result:
    """What a tool came to, on its way back to the narrator."""

    call: Call
    summary: str
    failed: bool = False


@dataclass
class Prompt:
    """Everything the narrator is told, assembled from things that are true."""

    briefing: str
    # Which model to ask. Travels with the turn rather than being read from
    # the environment at the last moment, because two campaigns on one
    # deployment can be on different ones.
    model: str
    system_slug: str
    module_slug: str
    module_title: str
    module_premise: str
    world: str
    # What the player just said, verbatim. The transcript holds it too, but
    # sanitised — and the double's instructions are exactly what sanitising
    # removes, so it has to arrive by a route that does not go through
    # storage.
    message: str = ""
    # (role, content) oldest first, the current turn included. This scene's
    # turns and no others: prose stops being memory at a scene boundary, and
    # what carries across one is the world and the recaps below.
    transcript: list[tuple[str, str]] = field(default_factory=list)
    # What this scene is called, when anybody named it.
    scene_title: str = ""
    # (title, recap) for the scenes already closed, oldest first. A campaign's
    # long memory, at a few sentences each rather than every word.
    recaps: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class Recap:
    """What happened in a scene, in the few sentences that outlive it."""

    text: str


class Narrator(Protocol):
    name: str

    def sanitise(self, message: str) -> str:
        """The player's message as it should be stored.

        Exists because the double reads its instructions out of the message
        and those must never reach a transcript. A real narrator has nothing
        to take out and returns it unchanged — but the router must not have
        to know which kind it is holding.
        """
        ...

    def narrate(
        self, prompt: Prompt
    ) -> AsyncGenerator[Said | Calls | Refused, list[Result] | None]:
        """Describe what happens, asking for what it needs along the way.

        Yields prose as it is produced and ``Calls`` when it wants something
        run. The caller sends back a list of ``Result``, one per call, in the
        order asked.

        Raises NarrationError when there is no answer at all — which the
        caller turns into an event on the open stream, because by then the
        status line is long gone.
        """
        ...

    def close(
        self, prompt: Prompt
    ) -> AsyncGenerator[Calls | Recap, list[Result] | None]:
        """Sum up a scene, and record what it narrated but never recorded.

        Driven exactly as ``narrate`` is, and for exactly the same reason:
        what it proposes goes through the same engines and is refused by the
        same refusals. The difference is only which tools are offered — see
        ``CLOSING_TOOLS`` — and that it ends with a ``Recap`` rather than
        prose.

        This is the last moment at which a fact gary narrated but never wrote
        down can still be written down. After the scene closes the transcript
        is out of context and that fact is gone.

        Raises NarrationError like ``narrate``. The caller closes the scene
        anyway: a scene missing its recap is a worse campaign, and a scene
        that would not close is an unbounded one.
        """
        ...
