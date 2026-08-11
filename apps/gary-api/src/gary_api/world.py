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

from gary_api.models import Adversary, Character, WorldEvent


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
# A scene boundary. Nothing about the world changes here, which is why it
# projects to nothing — but "when did the story turn a corner" is a question
# the history should answer in order with everything else.
SCENED = "scene-began"

# A fight, as three things that happen to it. The order is decided once, by
# the engine, and written down here — so "whose turn is it" is a fold over
# the log like everything else rather than a column somebody advances.
FOUGHT = "fight-began"
TURNED = "turn-ended"
PEACE = "fight-ended"

KINDS = (
    MOVED, REMEMBERED, FORGOTTEN, DAMAGED, HEALED, AFFLICTED, RELIEVED,
    ELAPSED, SCENED, FOUGHT, TURNED, PEACE,
)


@dataclass
class Fighter:
    """The parts of anybody the log can change.

    Shared by the party and by what they are fighting so that damage, healing
    and conditions fold one way rather than two. The sheets they come from
    are different tables and different shapes; what happens to them is the
    same thing happening.
    """

    id: str
    name: str
    max_hp: int
    hp: int
    conditions: list[str] = field(default_factory=list)

    @property
    def down(self) -> bool:
        return self.hp <= 0


@dataclass
class Member(Fighter):
    """A character as they currently stand."""

    character_class: str = ""
    level: int = 1
    # Who speaks for them. Part of the world rather than beside it, because
    # it is a fact about the table that gary needs on every turn — and the
    # world is what gary is told on every turn.
    played_by: str = "gary"


@dataclass
class Foe(Fighter):
    """Something being fought, as it currently stands."""

    armour_class: int = 10
    attack_bonus: int = 0
    damage: str = "1d6"


@dataclass
class Fight:
    """A fight in progress: who is in it, in what order, and where it is up to.

    ``order`` holds ids of party members and adversaries alike, because turn
    order does not care which side somebody is on — that is the whole reason
    initiative exists.
    """

    order: list[str] = field(default_factory=list)
    at: int = 0
    round: int = 1

    @property
    def whose(self) -> str:
        return self.order[self.at] if self.order else ""


@dataclass
class World:
    place: str = ""
    facts: dict[str, str] = field(default_factory=dict)
    minutes: int = 0
    party: list[Member] = field(default_factory=list)
    enemies: list[Foe] = field(default_factory=list)
    # None when nobody is fighting, which is most of the time.
    fight: Fight | None = None

    def member(self, character_id: str) -> Member | None:
        for candidate in self.party:
            if candidate.id == character_id:
                return candidate
        return None

    def foe(self, adversary_id: str) -> Foe | None:
        for candidate in self.enemies:
            if candidate.id == adversary_id:
                return candidate
        return None

    def anyone(self, id_: str) -> Fighter | None:
        """Whoever that is, on either side."""
        return self.member(id_) or self.foe(id_)


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


def _id(payload: dict, key: str) -> str:
    raw = _text(payload, key)
    try:
        return str(uuid.UUID(raw))
    except ValueError:
        raise WorldError(f"{raw!r} is not a character") from None


def _who(payload: dict) -> dict:
    """Whichever side the event names, normalised, and exactly one of them.

    Two keys rather than one generic id, because a bare uuid in a log tells
    you nothing about what to look it up in — and a history somebody reads a
    year from now is most of the point of keeping one.
    """
    keys = [key for key in ("character_id", "adversary_id") if payload.get(key)]
    if len(keys) != 1:
        raise WorldError("an event names exactly one character or adversary")
    return {keys[0]: _id(payload, keys[0])}


def _order(payload: dict) -> list[str]:
    order = payload.get("order")
    if not isinstance(order, list) or not order:
        raise WorldError("a fight needs somebody in it")
    return [_id({"id": one}, "id") for one in order]


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
        return {**_who(payload), "amount": _count(payload, "amount")}
    if kind in (AFFLICTED, RELIEVED):
        return {
            **_who(payload),
            "condition": _text(payload, "condition").lower(),
        }
    if kind == FOUGHT:
        return {"order": _order(payload)}
    if kind in (TURNED, PEACE):
        # Nothing to carry. What they mean is entirely where they sit in the
        # log, which is the one thing a payload could not express.
        return {}
    if kind == SCENED:
        # The one field here that may be blank. A scene nobody named is
        # ordinary — the first one never is — and refusing it would make the
        # log demand a title the game does not.
        title = payload.get("title")
        return {"title": title.strip() if isinstance(title, str) else ""}
    return {"minutes": _count(payload, "minutes")}


async def record(
    database: AsyncSession,
    campaign_id: uuid.UUID,
    kind: str,
    payload: dict | None = None,
    turn_id: uuid.UUID | None = None,
    scene_id: uuid.UUID | None = None,
) -> WorldEvent:
    """Write one thing that happened."""
    # Checked before the database is touched, not after. A refusal is the
    # common case when a model is proposing these, and doing the work first
    # only to throw it away is both slower and easier to misread as a write
    # that half happened.
    cleaned = clean(kind, payload)

    highest = await database.scalar(
        select(func.coalesce(func.max(WorldEvent.seq), 0)).where(
            WorldEvent.campaign_id == campaign_id
        )
    )

    event = WorldEvent(
        campaign_id=campaign_id,
        seq=(highest or 0) + 1,
        kind=kind,
        payload=cleaned,
        turn_id=turn_id,
        scene_id=scene_id,
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
    adversaries = await database.scalars(
        select(Adversary)
        .where(Adversary.campaign_id == campaign_id)
        .order_by(Adversary.created_at, Adversary.name)
    )
    return project(
        list(characters),
        await history(database, campaign_id),
        list(adversaries),
    )


def _advance(world: World) -> None:
    """Move a fight on to the next one still standing.

    Skipping the fallen is a rule rather than bookkeeping — a fight that
    stopped on somebody at nought hit points and waited for them to act would
    never move again — and it lives here because the log is the only thing
    that knows both the order and who is down.
    """
    fight = world.fight
    if fight is None:
        return

    for _ in range(len(fight.order)):
        fight.at += 1
        if fight.at >= len(fight.order):
            fight.at = 0
            fight.round += 1
        standing = world.anyone(fight.whose)
        if standing is None or not standing.down:
            return

    # Everybody in the order is down, which the engine ends the fight over
    # before this can be reached twice. Left rather than raised: a fold over
    # a log is not the place to start refusing history.


def project(
    characters: list[Character],
    events: list[WorldEvent],
    adversaries: list | None = None,
) -> World:
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
                played_by=character.played_by,
            )
            for character in characters
        ],
        enemies=[
            Foe(
                id=str(adversary.id),
                name=adversary.name,
                max_hp=adversary.max_hp,
                hp=adversary.max_hp,
                armour_class=adversary.armour_class,
                attack_bonus=adversary.attack_bonus,
                damage=adversary.damage,
            )
            for adversary in adversaries or []
        ],
    )

    for event in events:
        payload = event.payload or {}
        kind = event.kind

        if kind == SCENED:
            # A boundary is in the log so the history reads in order, but it
            # changes nothing about the world — that is the point of it. Named
            # here rather than left to fall through the chain below and miss,
            # which would work by accident.
            continue

        if kind == MOVED:
            world.place = payload["place"]
        elif kind == REMEMBERED:
            world.facts[payload["key"]] = payload["value"]
        elif kind == FORGOTTEN:
            world.facts.pop(payload["key"], None)
        elif kind == ELAPSED:
            world.minutes += payload["minutes"]
        elif kind == FOUGHT:
            world.fight = Fight(order=list(payload["order"]))
        elif kind == TURNED:
            _advance(world)
        elif kind == PEACE:
            world.fight = None
        else:
            member = world.anyone(
                payload.get("character_id") or payload.get("adversary_id") or ""
            )
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
            else:
                # RELIEVED, and nothing else: clean() refuses any kind not in
                # KINDS before it is written, so the chain is exhaustive and
                # an elif here would leave an unreachable branch.
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
            # Said on every line rather than in a note underneath, because
            # this is the one fact about the party gary must never lose track
            # of: whose choices are not its to make.
            whose = (
                "PLAYED BY THE PLAYER — never decide what they do"
                if member.played_by == "player"
                else "yours to play"
            )
            lines.append(
                f"  - {member.name}, level {member.level} {member.character_class}"
                f" ({state}) — {whose}"
            )
    else:
        lines.append("The party: nobody yet")

    if world.facts:
        lines.append("Established facts:")
        for key in sorted(world.facts):
            lines.append(f"  - {key}: {world.facts[key]}")

    # A fight, if there is one. Stated every turn for the same reason the
    # party's hit points are: gary running an encounter from what the last few
    # paragraphs implied is exactly where a fight goes wrong, and the order is
    # the first thing to slip.
    if world.fight:
        fight = world.fight
        lines.append(f"A fight is happening. Round {fight.round}.")
        lines.append("Order:")
        for index, who in enumerate(fight.order):
            standing = world.anyone(who)
            if standing is None:
                continue
            mark = " <-- it is their turn" if index == fight.at else ""
            state = "down" if standing.down else f"{standing.hp}/{standing.max_hp}"
            lines.append(f"  {index + 1}. {standing.name} ({state}){mark}")

        up = world.anyone(fight.whose)
        if isinstance(up, Member) and up.played_by == "player":
            # The whole reason any of this is built. Said as its own line
            # rather than left to the marker above, because it is an
            # instruction and the rest is a table.
            lines.append(
                f"It is {up.name}'s turn, and {up.name} is the player's. "
                "Stop and ask them what they do. Do not decide it, do not "
                "end their turn, and do not narrate past it."
            )
    elif world.enemies:
        lines.append(
            "Not fighting. Previously fought: "
            + ", ".join(
                f"{foe.name} ({'down' if foe.down else f'{foe.hp}/{foe.max_hp}'})"
                for foe in world.enemies
            )
        )

    return "\n".join(lines)
