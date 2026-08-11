"""Rolling dice, so that gary does not have to.

A language model asked for a d20 gives a plausible number, which is exactly
the wrong thing when the number decides what happens: plausible is not
random, and a model that wants the scene to go well will roll well. So gary
asks for a roll and this rolls it.

``DICE_SEED`` makes a run reproducible, the same way ``IDENTITY_FAKE`` makes
sign-in reproducible. It is for the specs — without it a spec could only
assert that some number arrived, which is what it would assert if gary had
made one up.
"""

import os
import random
import re
from dataclasses import dataclass

# NdM, with an optional +K or -K. Nothing else: a model that asks for
# "1d20+lots" or "2d6 plus my proficiency" gets a clean refusal rather than a
# traceback, and the refusal is what reaches the player.
NOTATION = re.compile(r"^\s*(\d+)\s*d\s*(\d+)\s*(?:([+-])\s*(\d+))?\s*$", re.IGNORECASE)

# Enough for any real check, and small enough that a runaway request cannot
# spend the request thread building a list.
MAX_DICE = 100
MAX_SIDES = 1000


class DiceError(Exception):
    """A notation gary cannot roll."""


@dataclass(frozen=True)
class Roll:
    notation: str
    dice: tuple[int, ...]
    modifier: int
    total: int
    reason: str


_random = random.Random()


def configure() -> None:
    """Seed from the environment, if it says to.

    Called once at startup and again per scenario, so a seeded run starts
    from the same place every time rather than from wherever the last one
    left the generator.
    """
    raw = os.environ.get("DICE_SEED")
    seed(int(raw)) if raw else reseed()


def seed(value: int) -> None:
    """Roll from a known place."""
    global _random
    _random = random.Random(value)


def reseed() -> None:
    """Roll from an unknown one, which is the point outside a spec."""
    global _random
    _random = random.Random()


def modifier_in(notation: str) -> int:
    """What a notation adds, without rolling it.

    Asked so that a roll made for a person can be refused before any dice are
    thrown: what a character adds to a die is their sheet's to say, and a
    narrator supplying it is the one thing the engines exist to stop.
    """
    match = NOTATION.match(notation or "")
    if not match:
        raise DiceError(f"gary cannot roll {notation!r}")
    _, _, sign, amount = match.groups()
    return 0 if not amount else int(amount) * (-1 if sign == "-" else 1)


def roll(notation: str, reason: str = "") -> Roll:
    """Roll ``NdM+K`` and say what came up.

    The individual dice are kept and not just the total, because "17" and
    "a 14 and a 3" are different things to read in a transcript, and because
    a natural 20 is worth knowing about.
    """
    match = NOTATION.match(notation or "")
    if not match:
        raise DiceError(f"gary cannot roll {notation!r}")

    count, sides, sign, amount = match.groups()
    count, sides = int(count), int(sides)

    if not 1 <= count <= MAX_DICE:
        raise DiceError(f"gary will not roll {count} dice at once")
    if not 2 <= sides <= MAX_SIDES:
        raise DiceError(f"gary has no {sides}-sided die")

    modifier = int(amount or 0)
    if sign == "-":
        modifier = -modifier

    dice = tuple(_random.randint(1, sides) for _ in range(count))
    return Roll(
        notation=notation.strip(),
        dice=dice,
        modifier=modifier,
        total=sum(dice) + modifier,
        reason=reason.strip(),
    )
