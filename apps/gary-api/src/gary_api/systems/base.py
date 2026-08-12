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
class Method:
    """One way an edition lets you arrive at six numbers.

    Which of these exist is the system's to say. Not a global list with
    exceptions: an edition permits what it permits, and asking for one it does
    not offer is refused the way an unknown class is.

    ``generates`` is whether gary produces the numbers; ``arrange`` is whether
    you place them afterwards. Those are two questions and not one — rolling
    three dice straight down the page generates and does not arrange, and
    typing them in arranges without generating anything.
    """

    slug: str
    name: str
    blurb: str
    generates: bool
    arrange: bool


# Offered by every system, because it is not really a method: somebody who
# rolled at a real table, or built a character by a rule gary does not
# implement, has an answer already and needs somewhere to put it. It is free
# to offer, too — nothing downstream cares whether dice, a table or a person
# produced a score.
MANUAL = Method(
    slug="manual",
    name="Type them in",
    blurb="Enter six scores you worked out somewhere else.",
    generates=False,
    arrange=True,
)

STANDARD_ARRAY = Method(
    slug="standard-array",
    name="The standard array",
    blurb="15, 14, 13, 12, 10, 8 — put them where you like.",
    generates=True,
    arrange=True,
)

POINT_BUY = Method(
    slug="point-buy",
    name="Point buy",
    blurb="Spend a budget on scores, so two characters are comparable.",
    generates=False,
    arrange=True,
)

ROLL_4D6 = Method(
    slug="roll-4d6-drop-lowest",
    name="Roll 4d6, drop the lowest",
    blurb="Six sets of four dice, worst of each thrown away. Arrange as you like.",
    generates=True,
    arrange=True,
)

ROLL_3D6_IN_ORDER = Method(
    slug="roll-3d6-in-order",
    name="Roll 3d6 in order",
    blurb="Three dice, six times, straight down the page. You play what you got.",
    generates=True,
    arrange=False,
)

ARRAY = (15, 14, 13, 12, 10, 8)


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

    def modifier(self, score: int) -> int:
        """What an ability score is worth on a check, in this system.

        Here rather than at the caller because it is a rule, and rules differ:
        this is the whole argument for a system package instead of a paragraph
        in a prompt.
        """
        ...

    def initiative(self, modifier: int) -> Roll:
        """Roll for turn order. Raises SystemError if this system cannot."""
        ...

    def generate(self, method: str) -> list[dict]:
        """Six scores by that method, with the dice that made them.

        Raises SystemError if this system does not offer it, or if it does but
        produces nothing to generate — point buy and typing them in are both
        real methods that gary has no numbers for.
        """
        ...

    def hit_points(self, character_class: str, abilities: dict[str, int]) -> int:
        """What somebody of that class starts on.

        Handed the whole sheet rather than one score, because which ability
        hit points come off is this system's business and nobody else's.
        """
        ...

    def attack_bonus(self, abilities: dict[str, int]) -> int:
        """What a character adds to hit, from their own sheet."""
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

    def modifier(self, score: int) -> int:
        """The third-edition-onward formula, which 5e and Pathfinder kept."""
        return (score - 10) // 2

    # Which ability decides turn order. A system that uses a different one
    # says so here rather than anywhere caring what it is called.
    initiative_ability: str = "dex"

    def initiative(self, modifier: int) -> Roll:
        """One roll each, ordered highest first."""
        notation = f"{self.check_die}{modifier:+d}" if modifier else self.check_die
        return roll(notation, "initiative")

    # What this edition permits, in the order it should be offered. Typing
    # them in is appended rather than listed, because every system has it and
    # a system that forgot would be a system with no way in at all.
    #
    # Offering is not generating: point buy is a method an edition permits and
    # gary produces no numbers for, which is why `Method.generates` is a
    # separate question from being on this list.
    offers: tuple[Method, ...] = ()
    # Why, when nothing a system offers produces numbers. Empty for the ones
    # that do.
    cannot_generate: str = ""
    # What a score may be. Rolled ones cannot leave it; typed ones must not.
    scores: tuple[int, int] = (3, 18)
    # What each score costs under this edition's point buy, and what there is
    # to spend. Empty for a system that does not offer one. Published rather
    # than enforced here: the budget is a construction aid a client counts
    # while you spend, and what reaches the sheet is range-checked like any
    # other score. Anybody determined to hand-post an illegal spread can, and
    # is only cheating themselves.
    point_costs: dict[int, int] = {}
    point_budget: int = 0
    # Hit die by class, and what somebody with no entry gets. A class missing
    # from here is a class this system has not had its hit dice typed in yet,
    # which is a gap rather than a rule.
    hit_dice: dict[str, int] = {}
    default_hp: int = 8
    # What an ability nobody has set is worth, which is a system's to say —
    # ten is the d20 games' idea of average and not a universal one.
    default_score: int = 10
    # Which ability each of these comes off. Named here rather than spelled
    # into the router, because a system with a different vocabulary would
    # otherwise need the router changed to add it.
    hit_point_ability: str = "con"
    attack_ability: str = "str"
    # What a character without armour is worth hitting, and what an
    # unspecified swing does. Both are stated defaults rather than derived —
    # sheets carry no armour and no weapons yet — but they are the system's
    # stated defaults, not the router's.
    default_armour_class: int = 12
    unarmed_damage: str = "1d6"

    @property
    def methods(self) -> tuple[Method, ...]:
        return (*self.offers, MANUAL)

    def method(self, slug: str) -> Method:
        for offered in self.methods:
            if offered.slug == slug:
                return offered
        raise SystemError(f"{self.name} does not offer {slug!r}")

    def generate(self, method: str) -> list[dict]:
        wanted = self.method(method)
        if not wanted.generates:
            raise SystemError(f"there is nothing to generate for {wanted.name!r}")

        if wanted is STANDARD_ARRAY:
            # No dice, but the same shape as the rolled ones — a client should
            # not have to hold two ideas of what a score is.
            return [{"score": score, "dice": [], "dropped": None} for score in ARRAY]

        thrown = []
        for _ in self.abilities:
            if wanted is ROLL_3D6_IN_ORDER:
                made = roll("3d6", "ability score")
                thrown.append(
                    {"score": made.total, "dice": list(made.dice), "dropped": None}
                )
                continue
            # Four dice and the worst thrown away. Kept rather than summed
            # away, because "15" and "6, 5, 4 and a discarded 1" are different
            # things to read while you decide where to put it.
            made = roll("4d6", "ability score")
            faces = sorted(made.dice)
            thrown.append(
                {
                    "score": sum(faces[1:]),
                    "dice": list(made.dice),
                    "dropped": faces[0],
                }
            )
        return thrown

    def hit_points(self, character_class: str, abilities: dict[str, int]) -> int:
        """The hit die at full, plus the constitution modifier, never below one.

        A constitution penalty can be worse than a hit die is big, and a
        character created already dead is nobody's idea of a rule.
        """
        die = self.hit_dice.get(character_class)
        if die is None:
            return self.default_hp
        return max(1, die + self.modifier(self.score(abilities, self.hit_point_ability)))

    def attack_bonus(self, abilities: dict[str, int]) -> int:
        return self.modifier(self.score(abilities, self.attack_ability))

    def score(self, abilities: dict[str, int], ability: str) -> int:
        return (abilities or {}).get(ability, self.default_score)

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
