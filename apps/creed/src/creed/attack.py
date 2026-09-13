"""Working out an attack from the real profiles.

This is the half of "rules and stats" a language model is worst at unaided. It
will produce a wound roll one pip off and the answer will look exactly as
plausible as the right one, which is the reason for doing it in code and
handing back the number rather than the method.

Everything is expected values over a whole unit's attacks, not a simulation.
That is what somebody actually wants when choosing a target — "about six
wounds" decides the question, and a distribution does not decide it better.

The rule creed holds to: apply what it can read off the weapon, and name what
it could not. An answer that silently drops Sustained Hits is wrong in the
direction that loses games, and nothing about it looks wrong.
"""

import re
from dataclasses import dataclass, field

# Weapon abilities creed applies. Anything else on a weapon is named in the
# result as not applied, rather than quietly ignored.
MODELLED = (
    "torrent",
    "twin-linked",
    "sustained hits",
    "lethal hits",
    "devastating wounds",
    "rapid fire",
    "melta",
    "heavy",
    "assault",
    "pistol",
    "blast",
    "hazardous",
    "precision",
    "ignores cover",
    "indirect fire",
    "lance",
    "extra attacks",
    "psychic",
    "one shot",
    "anti-",
)

# Abilities that appear on a weapon and change no number in this calculation.
# Listed so that they are not reported as "not applied", which would be noise
# on almost every weapon and would train somebody to ignore the warning that
# matters.
NO_EFFECT_HERE = (
    "pistol",
    "assault",
    "heavy",
    "blast",
    "hazardous",
    "precision",
    "ignores cover",
    "indirect fire",
    "psychic",
    "one shot",
    "extra attacks",
    "lance",
    "rapid fire",
    "melta",
)

_DICE = re.compile(r"(?P<count>\d*)D(?P<sides>\d+)(?:\s*\+\s*(?P<bonus>\d+))?", re.I)
_NUMBER = re.compile(r"-?\d+")
_SUSTAINED = re.compile(r"sustained hits\s*(\d+|d\d+)", re.I)
_ANTI = re.compile(r"anti-(?P<keyword>[\w\- ]+?)\s*(?P<threshold>\d)\+", re.I)


class UnreadableProfileError(Exception):
    """A value in the profile creed will not guess at."""


def average(value: str | None, *, default: float | None = None) -> float:
    """The expected value of a stat that may be a dice expression.

    ``D6`` is 3.5, ``2D6`` is 7, ``D3+1`` is 3. A plain number is itself.
    """
    text = (value or "").strip()
    if not text:
        if default is not None:
            return default
        raise UnreadableProfileError("the profile left this value empty")
    match = _DICE.search(text)
    if match:
        count = int(match.group("count") or 1)
        sides = int(match.group("sides"))
        bonus = int(match.group("bonus") or 0)
        return count * (sides + 1) / 2 + bonus
    number = _NUMBER.search(text)
    if number:
        return float(number.group())
    raise UnreadableProfileError(f"creed cannot read {text!r} as a number")


def _target_number(text: str | None) -> int | None:
    """A roll like "3+" as the number needed. ``None`` when there is none."""
    if not text:
        return None
    match = _NUMBER.search(text)
    return int(match.group()) if match else None


def chance(needed: int | None) -> float:
    """The chance a d6 meets a target. A 1 always fails and a 6 always hits."""
    if needed is None:
        return 0.0
    needed = max(2, min(6, needed))
    return (7 - needed) / 6


def wound_target(strength: float, toughness: float) -> int:
    """The strength-versus-toughness table, which is the step most often wrong."""
    if strength >= toughness * 2:
        return 2
    if strength > toughness:
        return 3
    if strength == toughness:
        return 4
    if strength * 2 <= toughness:
        return 6
    return 5


@dataclass
class Step:
    label: str
    detail: str
    value: float | None = None


@dataclass
class Result:
    weapon: str
    attacker: str
    target: str
    attacks: float
    hit_needed: int | None
    wound_needed: int
    save_needed: int | None
    save_used: str
    expected_hits: float
    expected_wounds: float
    expected_unsaved: float
    expected_damage: float
    expected_kills: float
    steps: list[Step] = field(default_factory=list)
    applied: list[str] = field(default_factory=list)
    not_applied: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _abilities_on(weapon: dict) -> list[str]:
    """The weapon's abilities, which are in `description`, not in `type`.

    `type` is only ever "Ranged", "Melee" or empty. The abilities are a
    comma-separated list in the description: "LETHAL HITS: non-MONSTER/VEHICLE,
    Rapid Fire 1".
    """
    text = (weapon.get("profile") or weapon.get("description") or "").strip()
    return [part.strip() for part in text.split(",") if part.strip()]


def _is_conditional(ability: str) -> bool:
    """True when the ability only applies in a case creed cannot check.

    Wahapedia writes these as a qualifier after a colon — "LETHAL HITS:
    non-MONSTER/VEHICLE" applies against some targets and not others, and
    deciding which needs the whole target's keywords against a phrase written
    for a person. Applying it anyway is wrong in the direction that loses
    games, so creed does not, and says so.
    """
    return ":" in ability


def _has(lowered: list[str], name: str) -> bool:
    """Whether an unconditional ability of this name is on the weapon."""
    return any(
        plain.startswith(name) and not _is_conditional(plain) for plain in lowered
    )


def resolve(
    weapon: dict,
    target_model: dict,
    *,
    attacker: str = "",
    target: str = "",
    models: int = 1,
    target_keywords: tuple[str, ...] = (),
) -> Result:
    """One weapon, fired by ``models`` models, into one target profile."""
    abilities = _abilities_on(weapon)
    lowered = [ability.lower() for ability in abilities]

    attacks_each = average(weapon.get("A"))
    attacks = attacks_each * models

    toughness = average(target_model.get("T"))
    strength = average(weapon.get("S"))
    wound_needed = wound_target(strength, toughness)

    # Anti-X N+ makes a wound roll of N+ a critical wound against a target
    # with that keyword — which in practice means it wounds on that number.
    for ability in abilities:
        anti = _ANTI.search(ability)
        if anti and any(
            anti.group("keyword").strip().casefold() == keyword.casefold()
            for keyword in target_keywords
        ):
            wound_needed = min(wound_needed, int(anti.group("threshold")))

    hit_needed = _target_number(weapon.get("BS_WS"))
    torrent = _has(lowered, "torrent")
    hit_chance = 1.0 if torrent else chance(hit_needed)

    result = Result(
        weapon=weapon.get("name", ""),
        attacker=attacker,
        target=target,
        attacks=attacks,
        hit_needed=None if torrent else hit_needed,
        wound_needed=wound_needed,
        save_needed=None,
        save_used="",
        expected_hits=0.0,
        expected_wounds=0.0,
        expected_unsaved=0.0,
        expected_damage=0.0,
        expected_kills=0.0,
    )

    if torrent:
        result.applied.append("Torrent")
        result.steps.append(
            Step("hit", "Torrent: the weapon hits automatically, so no hit roll", 1.0)
        )
    else:
        result.steps.append(Step("hit", f"hits on {hit_needed}+", hit_chance))

    hits = attacks * hit_chance

    sustained = next(
        (
            _SUSTAINED.search(a)
            for a in abilities
            if _SUSTAINED.search(a) and not _is_conditional(a)
        ),
        None,
    )
    if sustained:
        extra = average(sustained.group(1))
        # A critical hit is an unmodified 6, so one sixth of the attacks each
        # generate this many additional hits.
        bonus = attacks * (1 / 6) * extra
        hits += bonus
        result.applied.append(f"Sustained Hits {sustained.group(1)}")
        result.steps.append(
            Step("sustained", f"6s to hit add {extra:g} hits each", bonus)
        )

    result.expected_hits = hits

    wound_chance = chance(wound_needed)
    if _has(lowered, "twin-linked"):
        # Re-rolling a failed wound gives a second chance at the same number.
        wound_chance = wound_chance + (1 - wound_chance) * wound_chance
        result.applied.append("Twin-linked")
        result.steps.append(
            Step(
                "wound",
                f"wounds on {wound_needed}+, re-rolling failures",
                wound_chance,
            )
        )
    else:
        result.steps.append(Step("wound", f"wounds on {wound_needed}+", wound_chance))

    lethal = _has(lowered, "lethal hits")
    if lethal:
        # A critical hit wounds automatically and skips the wound roll.
        auto = hits * (1 / 6)
        rest = (hits - auto) * wound_chance
        wounds = auto + rest
        result.applied.append("Lethal Hits")
        result.steps.append(Step("lethal", "6s to hit wound automatically", auto))
    else:
        wounds = hits * wound_chance
    result.expected_wounds = wounds

    armour = _target_number(target_model.get("Sv"))
    invulnerable = _target_number(target_model.get("invulnerable"))
    ap = int(average(weapon.get("AP"), default=0))
    modified = armour + abs(ap) if armour is not None else None

    if invulnerable is not None and (modified is None or invulnerable < modified):
        save_needed, save_used = invulnerable, "invulnerable"
    else:
        save_needed, save_used = modified, "armour"
    if save_needed is not None and save_needed > 6:
        save_needed, save_used = None, "none"
    result.save_needed = save_needed
    result.save_used = save_used
    save_chance = chance(save_needed) if save_needed is not None else 0.0
    result.steps.append(
        Step(
            "save",
            (
                f"no save: AP {ap} puts the {armour}+ off the table"
                if save_needed is None
                else f"saves on {save_needed}+ ({save_used})"
            ),
            1 - save_chance,
        )
    )

    devastating = _has(lowered, "devastating wounds")
    if devastating:
        # A critical wound is an unmodified 6 and allows no save.
        critical = wounds * (1 / 6)
        ordinary = (wounds - critical) * (1 - save_chance)
        unsaved = critical + ordinary
        result.applied.append("Devastating Wounds")
        result.steps.append(Step("devastating", "6s to wound allow no save", critical))
    else:
        unsaved = wounds * (1 - save_chance)
    result.expected_unsaved = unsaved

    damage_each = average(weapon.get("D"))
    wounds_on_target = average(target_model.get("W"), default=1.0)
    result.expected_damage = unsaved * damage_each
    # Damage does not carry from one model to the next, so a damage 3 weapon
    # into 1-wound models kills one model per unsaved wound and spills the
    # rest. Counting total damage instead would overstate it threefold.
    per_model = min(damage_each, wounds_on_target)
    result.expected_kills = unsaved * per_model / wounds_on_target
    if damage_each > wounds_on_target:
        result.notes.append(
            f"damage {damage_each:g} exceeds the target's {wounds_on_target:g} "
            "wounds; the excess is lost rather than carrying to the next model"
        )

    for ability, plain in zip(abilities, lowered, strict=True):
        if _is_conditional(ability):
            result.not_applied.append(
                f"{ability} (only applies in some cases; creed has not "
                "decided whether this target is one)"
            )
            continue
        if any(plain.startswith(quiet) for quiet in NO_EFFECT_HERE):
            continue
        if any(plain.startswith(known) for known in MODELLED):
            continue
        result.not_applied.append(ability)

    return result
