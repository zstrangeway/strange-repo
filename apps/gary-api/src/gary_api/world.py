"""What is true in a campaign right now.

The failure this exists to prevent: a chatbot GM's only memory is its own
prose, so the tenth turn contradicts the second and nobody can say which was
right. Here the transcript is prose and the world is state, and they are
different things.

The world is an append-only log, folded on read. Nothing overwrites, so a
character on 3 hit points is on 3 hit points because of a list of things that
happened, and that list is still there. There is no snapshot column to
disagree with the log, because there is no snapshot column — a campaign has
tens of events and folding them is free. When that stops being true, add a
snapshot; do not add one first.

The model proposes events and never writes them. Everything here is reachable
without a model at all, which is the point: it is code, and code can be
pinned down exactly.

Nothing in this module knows which system is running. Hit points and
conditions are common to every system gary runs; anything that is not goes in
``systems``.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gary_api.models import Character, WorldEvent


class WorldError(Exception):
    """An event that would not make sense, refused before it is written."""


MOVED = "party-moved"
REMEMBERED = "fact-set"
FORGOTTEN = "fact-cleared"
DAMAGED = "damaged"
HEALED = "healed"
AFFLICTED = "condition-added"
RELIEVED = "condition-removed"
ELAPSED = "time-passed"

KINDS = (MOVED, REMEMBERED, FORGOTTEN, DAMAGED, HEALED, AFFLICTED, RELIEVED, ELAPSED)


@dataclass
class Member:
    """A character as they currently stand."""

    id: str
    name: str
    character_class: str
    level: int
    max_hp: int
    hp: int
    conditions: list[str] = field(default_factory=list)

    @property
    def down(self) -> bool:
        return self.hp <= 0


@dataclass
class World:
    place: str = ""
    facts: dict[str, str] = field(default_factory=dict)
    minutes: int = 0
    party: list[Member] = field(default_factory=list)

    def member(self, character_id: str) -> Member | None:
        for candidate in self.party:
            if candidate.id == character_id:
                return candidate
        return None


def _text(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise WorldError(f"{key} is required")
    return value.strip()


def _count(payload: dict, key: str) -> int:
    value = payload.get(key)
    # bool is an int in Python and True would arrive as 1, which is not a
    # number anybody meant.
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise WorldError(f"{key} must be a whole number of at least 0")
    return value


def _who(payload: dict) -> str:
    raw = _text(payload, "character_id")
    try:
        return str(uuid.UUID(raw))
    except ValueError:
        raise WorldError(f"{raw!r} is not a character") from None


def clean(kind: str, payload: dict | None) -> dict:
    """Check an event before it is written, and normalise what it carries.

    Refusing here is what keeps the log worth folding: an event that cannot
    be applied is a hole in the world's history, and it is cheaper to refuse
    it than to teach every reader to skip it.
    """
    payload = payload or {}
    if kind not in KINDS:
        raise WorldError(f"{kind!r} is not something that happens")

    if kind == MOVED:
        return {"place": _text(payload, "place")}
    if kind == REMEMBERED:
        return {"key": _text(payload, "key"), "value": _text(payload, "value")}
    if kind == FORGOTTEN:
        return {"key": _text(payload, "key")}
    if kind in (DAMAGED, HEALED):
        return {"character_id": _who(payload), "amount": _count(payload, "amount")}
    if kind in (AFFLICTED, RELIEVED):
        return {
            "character_id": _who(payload),
            "condition": _text(payload, "condition").lower(),
        }
    return {"minutes": _count(payload, "minutes")}


async def record(
    database: AsyncSession,
    campaign_id: uuid.UUID,
    kind: str,
    payload: dict | None = None,
    turn_id: uuid.UUID | None = None,
) -> WorldEvent:
    """Write one thing that happened."""
    highest = await database.scalar(
        select(func.coalesce(func.max(WorldEvent.seq), 0)).where(
            WorldEvent.campaign_id == campaign_id
        )
    )

    event = WorldEvent(
        campaign_id=campaign_id,
        seq=(highest or 0) + 1,
        kind=kind,
        payload=clean(kind, payload),
        turn_id=turn_id,
    )
    database.add(event)
    await database.flush()
    return event


async def history(
    database: AsyncSession, campaign_id: uuid.UUID
) -> list[WorldEvent]:
    """Everything that happened, in the order it happened."""
    rows = await database.scalars(
        select(WorldEvent)
        .where(WorldEvent.campaign_id == campaign_id)
        .order_by(WorldEvent.seq)
    )
    return list(rows)


async def of(database: AsyncSession, campaign_id: uuid.UUID) -> World:
    """The world as it stands, folded out of everything that happened."""
    characters = await database.scalars(
        select(Character)
        .where(Character.campaign_id == campaign_id)
        .order_by(Character.created_at, Character.name)
    )
    return project(list(characters), await history(database, campaign_id))


def project(characters: list[Character], events: list[WorldEvent]) -> World:
    """Fold the log over the sheets.

    The sheets supply what does not change; the log supplies everything that
    did. An event naming a character who is not here is skipped rather than
    fatal — a character can be removed and the events they caused stay in the
    history, which is the correct reading of an append-only log.
    """
    world = World(
        party=[
            Member(
                id=str(character.id),
                name=character.name,
                character_class=character.character_class,
                level=character.level,
                max_hp=character.max_hp,
                hp=character.max_hp,
            )
            for character in characters
        ]
    )

    for event in events:
        payload = event.payload or {}
        kind = event.kind

        if kind == MOVED:
            world.place = payload["place"]
        elif kind == REMEMBERED:
            world.facts[payload["key"]] = payload["value"]
        elif kind == FORGOTTEN:
            world.facts.pop(payload["key"], None)
        elif kind == ELAPSED:
            world.minutes += payload["minutes"]
        else:
            member = world.member(payload.get("character_id", ""))
            if member is None:
                continue
            if kind == DAMAGED:
                # Nobody goes below nothing; hit points are not a debt.
                member.hp = max(0, member.hp - payload["amount"])
            elif kind == HEALED:
                # Nor above full; being healed past it is common and is not
                # an error, it just does not make anyone tougher than they are.
                member.hp = min(member.max_hp, member.hp + payload["amount"])
            elif kind == AFFLICTED:
                if payload["condition"] not in member.conditions:
                    member.conditions.append(payload["condition"])
            elif kind == RELIEVED:
                if payload["condition"] in member.conditions:
                    member.conditions.remove(payload["condition"])

    return world


def render(world: World) -> str:
    """The world as the model is shown it.

    Written out rather than handed over as JSON because this is going into a
    prompt, and a paragraph is read more reliably than a data structure. It
    is regenerated every turn from the log, so it cannot go stale the way a
    summary the model wrote about itself would.
    """
    lines = [
        f"Where the party is: {world.place or 'not yet established'}",
        f"Time elapsed: {world.minutes} minutes",
    ]

    if world.party:
        lines.append("The party:")
        for member in world.party:
            state = f"{member.hp}/{member.max_hp} hit points"
            if member.down:
                state += ", down"
            if member.conditions:
                state += ", " + ", ".join(sorted(member.conditions))
            lines.append(
                f"  - {member.name}, level {member.level} {member.character_class}"
                f" ({state})"
            )
    else:
        lines.append("The party: nobody yet")

    if world.facts:
        lines.append("Established facts:")
        for key in sorted(world.facts):
            lines.append(f"  - {key}: {world.facts[key]}")

    return "\n".join(lines)
