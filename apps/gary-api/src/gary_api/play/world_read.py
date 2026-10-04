"""Read-only world, transcript, scene, and history endpoints."""

import uuid

from sqlalchemy import func, select

from gary_api import auth, scenes, systems, world
from gary_api.models import Adversary, Campaign, Character, Scene, Turn
from gary_api.play.campaigns import _mine, _party
from gary_api.play.schemas import (
    EventResponse,
    NewScene,
    SceneResponse,
    TurnResponse,
    WorldResponse,
)


def _next_level(campaign: Campaign, level: int) -> int | None:
    """What the level after this one costs, or nothing to reach.

    Two different silences answer the same way on purpose: a system that does
    not price a level at all (add-1e, until its per-class tables are typed in)
    and somebody already at the top both have no next number, and a card has
    the same thing to say about each.
    """
    try:
        ruleset = systems.ruleset(campaign.system_slug)
        return ruleset.experience_for(level + 1)
    except systems.SystemError:
        return None


def _as_change(event, named: dict[str, str]) -> dict:
    """One world event in the shape the stream sends it.

    Whoever it names is named rather than identified, which is the only
    difference between what is stored and what is read: the log keeps an id
    because that is what can be checked, and a card shows a name because that
    is what somebody reads.
    """
    payload = dict(event.payload)
    for key in ("character_id", "adversary_id"):
        if key in payload:
            payload["character"] = named.get(payload.pop(key))
    return {"kind": event.kind, **payload}


def _as_scene(scene: Scene) -> dict:
    return {
        "id": scene.id,
        "number": scene.number,
        "title": scene.title,
        "recap": scene.recap,
        "open": scene.closed_at is None,
    }


async def read_world(
    campaign_id: uuid.UUID, database: auth.Db, user: auth.CurrentUser
) -> WorldResponse:
    campaign = await _mine(database, user, campaign_id)
    state = await world.of(database, campaign.id)
    return {
        "place": state.place,
        "minutes": state.minutes,
        "facts": state.facts,
        "party": [
            {
                "id": member.id,
                "name": member.name,
                "character_class": member.character_class,
                "level": member.level,
                "experience": member.experience,
                "next_level": _next_level(campaign, member.level),
                "hp": member.hp,
                "max_hp": member.max_hp,
                "conditions": member.conditions,
                "down": member.down,
                "played_by": member.played_by,
            }
            for member in state.party
        ],
        "enemies": [
            {
                "id": foe.id,
                "name": foe.name,
                "hp": foe.hp,
                "max_hp": foe.max_hp,
                "armour_class": foe.armour_class,
                "conditions": foe.conditions,
                "down": foe.down,
            }
            for foe in state.enemies
        ],
        "fight": (
            {
                "order": [
                    {
                        "id": who,
                        "name": (
                            state.anyone(who).name if state.anyone(who) else "?"
                        ),
                        "side": (
                            "party"
                            if isinstance(state.anyone(who), world.Member)
                            else "adversary"
                        ),
                    }
                    for who in state.fight.order
                ],
                "at": state.fight.at,
                "round": state.fight.round,
            }
            if state.fight
            else None
        ),
    }


async def read_transcript(
    campaign_id: uuid.UUID, database: auth.Db, user: auth.CurrentUser
) -> list[TurnResponse]:
    """Everything said so far, oldest first.

    A client that reloads mid-campaign has to get the table back, and the
    stream only carries what happens next.
    """
    campaign = await _mine(database, user, campaign_id)
    turns = await database.scalars(
        select(Turn)
        .where(Turn.campaign_id == campaign.id)
        .order_by(Turn.created_at, Turn.id)
    )
    # The log keeps ids because a name is not a key. The stream sends names
    # because everything downstream of it is something a person reads, so a
    # reloaded turn has to say the same thing the live one did.
    named = {
        str(one.id): one.name
        for one in (await _party(database, campaign.id))
        + list(
            await database.scalars(
                select(Adversary).where(Adversary.campaign_id == campaign.id)
            )
        )
    }
    return [
        {
            "id": turn.id,
            "role": turn.role,
            "content": turn.content,
            "complete": turn.complete,
            "scene_id": turn.scene_id,
            # Beside the turn they happened in, so a reloaded transcript shows
            # a roll as a roll rather than losing it into the prose.
            "rolls": [
                {
                    "notation": roll.notation,
                    "dice": roll.dice,
                    "modifier": roll.modifier,
                    "total": roll.total,
                    "reason": roll.reason,
                    "dc": roll.dc,
                    "degree": roll.degree,
                    # The same shape the stream sent, so a reload shows what
                    # was on screen a moment ago rather than a plainer
                    # version of it.
                    "character": (
                        roll.character.name
                        if roll.character
                        else roll.adversary.name if roll.adversary else None
                    ),
                    "ability": roll.ability,
                }
                for roll in turn.rolls
            ],
            # The same shape the stream sent, for the same reason the rolls
            # are: a reloaded turn should read like the one that was on
            # screen a moment ago.
            "changes": [
                _as_change(event, named) for event in turn.events
            ],
        }
        for turn in turns
    ]


async def read_scenes(
    campaign_id: uuid.UUID, database: auth.Db, user: auth.CurrentUser
) -> list[SceneResponse]:
    """Every scene, oldest first, with what each is remembered by."""
    campaign = await _mine(database, user, campaign_id)
    # Reading opens the first scene if there is not one yet, which is the same
    # answer a campaign gives to its first turn — a campaign is always in a
    # scene, and it would be odd for looking to be the thing that decides.
    await scenes.current(database, campaign.id)
    await database.commit()
    return [_as_scene(scene) for scene in await scenes.all_of(database, campaign.id)]


async def begin_scene(
    campaign_id: uuid.UUID,
    request: NewScene,
    database: auth.Db,
    user: auth.CurrentUser,
) -> SceneResponse:
    """End the scene being played and start the next one.

    Closing runs the reconciliation pass, so this can take as long as a model
    takes — it is the one request here that is slow on purpose.
    """
    from gary_api.play.campaigns import _playable
    from gary_api.play.engine import _run

    campaign = await _mine(database, user, campaign_id)

    # Same refusals as playing, for the same reason: a scene is a stretch of
    # play, and there is nobody to play it.
    party = await _party(database, campaign.id)
    _playable(party)

    opened = await scenes.begin(database, campaign, party, _run, request.title)
    await database.commit()
    return _as_scene(opened)


async def read_history(
    campaign_id: uuid.UUID, database: auth.Db, user: auth.CurrentUser
) -> list[EventResponse]:
    """Everything that happened, in the order it happened.

    The log is the point. A state anyone can overwrite is a state nobody can
    explain, and "why does gary think that" is the question this answers.
    """
    campaign = await _mine(database, user, campaign_id)
    return [
        {
            "seq": event.seq,
            "kind": event.kind,
            "payload": event.payload or {},
            "scene_id": event.scene_id,
        }
        for event in await world.history(database, campaign.id)
    ]
