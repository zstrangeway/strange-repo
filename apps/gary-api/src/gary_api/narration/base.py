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
}


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
    # (role, content) oldest first, the current turn included. The transcript
    # is prose; the world is state. Both are sent, because they answer
    # different questions.
    transcript: list[tuple[str, str]] = field(default_factory=list)


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
