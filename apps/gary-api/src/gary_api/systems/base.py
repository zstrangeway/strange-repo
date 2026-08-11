"""What a system has to say for itself.

A system is one file. It carries both halves — what the system *is* (its
name, its classes, the modules written for it) and what the system *does*
(how a check resolves) — because splitting them means adding a system in two
places and forgetting the second.

Nothing outside this package may branch on which system is running. gary
narrates, the world remembers, and the rules adjudicate; only the last of
those knows a d20 from a saving throw. ``tests/test_pluggable.py`` enforces
that, because it is the kind of rule that erodes one convenient ``if`` at a
time.

Adding a system therefore means: subclass one of the resolvers below, fill in
the data, add it to the registry. Nothing else in gary changes.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from gary_api.dice import Roll, roll


class SystemError(Exception):
    """Something was asked for that no registered system provides."""


class Degree(StrEnum):
    """How well a check went.

    Four, so that a system with four can say so. A system with two uses two
    and never mentions the others — what a system does not resolve, it does
    not return.
    """

    CRITICAL_SUCCESS = "critical-success"
    SUCCESS = "success"
    FAILURE = "failure"
    CRITICAL_FAILURE = "critical-failure"


@dataclass(frozen=True)
class Module:
    slug: str
    title: str
    # A premise and not a plot: the module sets a situation, and what happens
    # in it is the game.
    premise: str
    # Why this party is standing in that situation tonight, who wants it
    # dealt with, and what happens if nobody does.
    #
    # Separate from the premise because they answer different questions, and
    # the game only starts when the second one has an answer. Without it gary
    # opens on scenery and, asked "why am I here", says "maybe you have your
    # own reasons" — which is the one thing a game master must not hand back.
    # It is not the model's to invent, so the module says it.
    hook: str
    # Where the party is standing when the campaign begins. The world needs
    # somewhere to start and this is the only place that knows one; letting
    # the model pick would mean the first fact about the world came from the
    # least reliable thing in the system.
    opening: str


@dataclass(frozen=True)
class Outcome:
    reason: str
    dc: int
    roll: Roll
    degree: Degree


class Ruleset(Protocol):
    slug: str
    name: str
    blurb: str
    abilities: tuple[str, ...]
    classes: tuple[str, ...]
    modules: tuple[Module, ...]
    degrees: tuple[Degree, ...]

    def resolve(self, *, dc: int, modifier: int, reason: str) -> Outcome:
        """Roll this system's check die against a difficulty and grade it."""
        ...

    def briefing(self) -> str:
        """What the model is told about running this system.

        Assembled from the system rather than written into a prompt, so the
        narrator has nothing system-specific in it and a new system arrives
        already able to describe itself.
        """
        ...


class D20Ruleset:
    """The shared parts of every d20 system gary runs.

    Subclasses supply the data and pick a grader. A system that does not roll
    a d20 at all implements Ruleset directly and is no harder to register.
    """

    slug: str = ""
    name: str = ""
    blurb: str = ""
    abilities: tuple[str, ...] = ("str", "dex", "con", "int", "wis", "cha")
    classes: tuple[str, ...] = ()
    modules: tuple[Module, ...] = ()
    degrees: tuple[Degree, ...] = (Degree.SUCCESS, Degree.FAILURE)
    check_die: str = "1d20"

    def resolve(self, *, dc: int, modifier: int, reason: str) -> Outcome:
        notation = f"{self.check_die}{modifier:+d}" if modifier else self.check_die
        made = roll(notation, reason)
        return Outcome(reason=reason, dc=dc, roll=made, degree=self.grade(made, dc))

    def grade(self, made: Roll, dc: int) -> Degree:
        raise NotImplementedError

    def briefing(self) -> str:
        listed = ", ".join(degree.value for degree in self.degrees)
        return (
            f"You are running {self.name}.\n\n{self.blurb}\n\n"
            f"Checks roll {self.check_die} plus a modifier against a difficulty "
            f"class, and resolve to one of: {listed}. You never decide a "
            f"degree yourself — call the check tool and narrate what it "
            f"returns."
        )


class TwoDegrees(D20Ruleset):
    """Met the number or did not.

    5e and 3.5e have no critical successes on ability checks by the book, and
    inventing them would be a house rule gary imposed on every table.
    """

    degrees = (Degree.SUCCESS, Degree.FAILURE)

    def grade(self, made: Roll, dc: int) -> Degree:
        return Degree.SUCCESS if made.total >= dc else Degree.FAILURE


class FourDegrees(D20Ruleset):
    """Ten over is a critical success, ten under a critical failure.

    A natural 20 shifts the result one step better and a natural 1 one step
    worse, applied after the comparison rather than instead of it — which is
    what makes a natural 20 on a hopeless check a plain failure rather than a
    triumph.
    """

    degrees = (
        Degree.CRITICAL_SUCCESS,
        Degree.SUCCESS,
        Degree.FAILURE,
        Degree.CRITICAL_FAILURE,
    )

    LADDER = (
        Degree.CRITICAL_FAILURE,
        Degree.FAILURE,
        Degree.SUCCESS,
        Degree.CRITICAL_SUCCESS,
    )

    def grade(self, made: Roll, dc: int) -> Degree:
        if made.total >= dc + 10:
            degree = Degree.CRITICAL_SUCCESS
        elif made.total >= dc:
            degree = Degree.SUCCESS
        elif made.total > dc - 10:
            degree = Degree.FAILURE
        else:
            degree = Degree.CRITICAL_FAILURE

        natural = made.dice[0]
        if natural == 20:
            return self.shift(degree, 1)
        if natural == 1:
            return self.shift(degree, -1)
        return degree

    def shift(self, degree: Degree, by: int) -> Degree:
        at = self.LADDER.index(degree) + by
        return self.LADDER[max(0, min(len(self.LADDER) - 1, at))]
