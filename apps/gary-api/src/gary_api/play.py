"""The catalogue, campaigns, the characters in them, and the world.

Everything here reaches its campaign first, and a campaign that is not yours
answers 404 rather than 403. A 403 would confirm it exists, and whether a
stranger has a campaign is not yours to learn.

Nothing in this module names a system. It asks the registry, which is what
lets a new system arrive as one file — see ``tests/test_pluggable.py``, which
fails the build if that stops being true.
"""

import json
import uuid
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from gary_api import db, dice, logs, narration, systems, world
from gary_api.auth import CurrentUser, Db, Refusal
from gary_api.models import Campaign, Character, Roll, Turn

logger = logs.get_logger(__name__)

router = APIRouter(tags=["play"])

# What a character starts with when nobody says otherwise. Deriving hit points
# from class and constitution is the rules engine's job and it does not do
# that yet, so this is a stated default rather than a guess dressed as one.
DEFAULT_HP = 8
DEFAULT_ABILITY = 10


class ModuleResponse(BaseModel):
    slug: str
    title: str
    premise: str
    opening: str


class SystemResponse(BaseModel):
    slug: str
    name: str
    blurb: str
    classes: list[str]
    abilities: list[str]
    degrees: list[str]
    modules: list[ModuleResponse]


class NewCampaign(BaseModel):
    name: str = Field(max_length=120)
    system: str = Field(max_length=64)
    module: str = Field(max_length=64)

    @field_validator("name")
    @classmethod
    def not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("A campaign needs a name")
        return cleaned


class CampaignResponse(BaseModel):
    id: uuid.UUID
    name: str
    system: str
    module: str
    title: str
    turns: int


class NewCharacter(BaseModel):
    name: str = Field(max_length=80)
    character_class: str = Field(max_length=40)
    level: int = Field(default=1, ge=1, le=30)
    max_hp: int = Field(default=DEFAULT_HP, ge=1, le=999)
    abilities: dict[str, int] | None = None

    @field_validator("name")
    @classmethod
    def not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("A character needs a name")
        return cleaned


class CharacterResponse(BaseModel):
    id: uuid.UUID
    name: str
    character_class: str
    level: int
    max_hp: int
    abilities: dict[str, int]


class MemberResponse(BaseModel):
    id: str
    name: str
    character_class: str
    level: int
    hp: int
    max_hp: int
    conditions: list[str]
    down: bool


class WorldResponse(BaseModel):
    place: str
    minutes: int
    facts: dict[str, str]
    party: list[MemberResponse]


class EventResponse(BaseModel):
    seq: int
    kind: str
    payload: dict[str, Any]


def _as_system(ruleset: systems.Ruleset) -> dict:
    return {
        "slug": ruleset.slug,
        "name": ruleset.name,
        "blurb": ruleset.blurb,
        "classes": list(ruleset.classes),
        "abilities": list(ruleset.abilities),
        "degrees": [degree.value for degree in ruleset.degrees],
        "modules": [
            {
                "slug": module.slug,
                "title": module.title,
                "premise": module.premise,
                "opening": module.opening,
            }
            for module in ruleset.modules
        ],
    }


def _as_campaign(campaign: Campaign, turns: int = 0) -> dict:
    # The title is looked up rather than stored: it belongs to the module, and
    # a copy in the database is a copy that goes stale when the module is
    # reworded.
    module = systems.module(campaign.system_slug, campaign.module_slug)
    return {
        "id": campaign.id,
        "name": campaign.name,
        "system": campaign.system_slug,
        "module": campaign.module_slug,
        "title": module.title,
        "turns": turns,
    }


def _as_character(character: Character) -> dict:
    return {
        "id": character.id,
        "name": character.name,
        "character_class": character.character_class,
        "level": character.level,
        "max_hp": character.max_hp,
        "abilities": character.abilities or {},
    }


async def _mine(database, user, campaign_id: uuid.UUID) -> Campaign:
    """The campaign, if it is yours. 404 if it is not, or is not there."""
    found = await database.get(Campaign, campaign_id)
    if found is None or found.user_id != user.id:
        raise Refusal(
            status.HTTP_404_NOT_FOUND, "no_such_campaign", "No such campaign"
        )
    return found


@router.get("/catalogue")
async def read_catalogue() -> list[SystemResponse]:
    # No session: this is the menu, and what gary can play is the thing that
    # decides whether to make an account, not something an account unlocks.
    return [_as_system(ruleset) for ruleset in systems.rulesets()]


@router.get("/catalogue/{slug}")
async def read_system(slug: str) -> SystemResponse:
    try:
        return _as_system(systems.ruleset(slug))
    except systems.SystemError as error:
        raise Refusal(
            status.HTTP_404_NOT_FOUND, "no_such_system", str(error)
        ) from error


@router.post("/campaigns", status_code=status.HTTP_201_CREATED)
async def start_campaign(
    request: NewCampaign, database: Db, user: CurrentUser
) -> CampaignResponse:
    try:
        module = systems.module(request.system, request.module)
    except systems.SystemError as error:
        # Which half was wrong matters to whoever is filling in the form: a
        # system gary does not run is a different mistake from a module that
        # belongs to a different system.
        known = any(
            ruleset.slug == request.system for ruleset in systems.rulesets()
        )
        raise Refusal(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "no_such_module" if known else "no_such_system",
            str(error),
        ) from error

    campaign = Campaign(
        user_id=user.id,
        name=request.name,
        system_slug=request.system,
        module_slug=request.module,
    )
    database.add(campaign)
    await database.flush()

    # The world starts where the module says it starts. Letting the model
    # choose would mean the first fact about the world came from the least
    # reliable thing in the system.
    await world.record(database, campaign.id, world.MOVED, {"place": module.opening})
    await database.commit()

    return _as_campaign(campaign)


@router.get("/campaigns")
async def list_campaigns(database: Db, user: CurrentUser) -> list[CampaignResponse]:
    rows = await database.scalars(
        select(Campaign)
        .where(Campaign.user_id == user.id)
        .order_by(Campaign.created_at.desc())
    )
    return [_as_campaign(campaign) for campaign in rows]


@router.get("/campaigns/{campaign_id}")
async def read_campaign(
    campaign_id: uuid.UUID, database: Db, user: CurrentUser
) -> CampaignResponse:
    campaign = await _mine(database, user, campaign_id)
    turns = await database.scalar(
        select(func.count()).select_from(Turn).where(Turn.campaign_id == campaign.id)
    )
    return _as_campaign(campaign, turns or 0)


@router.post(
    "/campaigns/{campaign_id}/characters", status_code=status.HTTP_201_CREATED
)
async def add_character(
    campaign_id: uuid.UUID, request: NewCharacter, database: Db, user: CurrentUser
) -> CharacterResponse:
    campaign = await _mine(database, user, campaign_id)

    try:
        # Asked of the system rather than checked against a list here, so a
        # warlock is fine in a game that has warlocks and refused in one that
        # does not — before play, rather than mid-scene.
        spelled = systems.character_class(
            campaign.system_slug, request.character_class
        )
    except systems.SystemError as error:
        raise Refusal(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "no_such_class", str(error)
        ) from error

    ruleset = systems.ruleset(campaign.system_slug)
    abilities = request.abilities or {
        ability: DEFAULT_ABILITY for ability in ruleset.abilities
    }

    character = Character(
        campaign_id=campaign.id,
        name=request.name,
        character_class=spelled,
        level=request.level,
        max_hp=request.max_hp,
        abilities=abilities,
    )
    database.add(character)
    await database.commit()

    return _as_character(character)


@router.get("/campaigns/{campaign_id}/characters")
async def read_party(
    campaign_id: uuid.UUID, database: Db, user: CurrentUser
) -> list[CharacterResponse]:
    campaign = await _mine(database, user, campaign_id)
    rows = await database.scalars(
        select(Character)
        .where(Character.campaign_id == campaign.id)
        .order_by(Character.created_at, Character.name)
    )
    return [_as_character(character) for character in rows]


@router.get("/campaigns/{campaign_id}/world")
async def read_world(
    campaign_id: uuid.UUID, database: Db, user: CurrentUser
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
                "hp": member.hp,
                "max_hp": member.max_hp,
                "conditions": member.conditions,
                "down": member.down,
            }
            for member in state.party
        ],
    }


@router.get("/campaigns/{campaign_id}/history")
async def read_history(
    campaign_id: uuid.UUID, database: Db, user: CurrentUser
) -> list[EventResponse]:
    """Everything that happened, in the order it happened.

    The log is the point. A state anyone can overwrite is a state nobody can
    explain, and "why does gary think that" is the question this answers.
    """
    campaign = await _mine(database, user, campaign_id)
    return [
        {"seq": event.seq, "kind": event.kind, "payload": event.payload or {}}
        for event in await world.history(database, campaign.id)
    ]


# ------------------------------------------------------------------ playing


class NewTurn(BaseModel):
    message: str = Field(max_length=4000)

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Say something")
        return cleaned


def _frame(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _named(party: list[Character], name: str) -> Character:
    wanted = (name or "").strip().lower()
    for character in party:
        if character.name.lower() == wanted:
            return character
    raise world.WorldError(f"nobody here is called {name!r}")


async def _run(
    database, campaign: Campaign, party: list[Character], call, turn_id: uuid.UUID
) -> tuple[narration.Result, list[str]]:
    """Do what the narrator asked, or refuse it, and say what came of it.

    Everything a narrator can change goes through here, which is the whole
    arrangement: the model proposes, the engines decide, and what goes back to
    the model is what actually happened rather than what it suggested.
    """
    arguments = call.arguments or {}

    async def moved(kind: str, payload: dict, summary: str):
        await world.record(database, campaign.id, kind, payload, turn_id)
        return narration.Result(call, summary), [
            _frame("world", {"kind": kind, **payload})
        ]

    try:
        if call.name == "roll":
            made = dice.roll(arguments.get("notation", ""), arguments.get("reason", ""))
            database.add(
                Roll(
                    turn_id=turn_id,
                    notation=made.notation,
                    dice=list(made.dice),
                    modifier=made.modifier,
                    total=made.total,
                    reason=made.reason,
                )
            )
            await database.flush()
            return narration.Result(
                call, f"{made.notation} came up {made.total}"
            ), [
                _frame(
                    "roll",
                    {
                        "notation": made.notation,
                        "dice": list(made.dice),
                        "modifier": made.modifier,
                        "total": made.total,
                        "reason": made.reason,
                    },
                )
            ]

        if call.name == "check":
            # The rules grade it, not gary and not this module. A system with
            # four degrees returns four here without anything else changing.
            ruleset = systems.ruleset(campaign.system_slug)
            character = _named(party, arguments.get("character", ""))
            dc = arguments.get("dc")
            if isinstance(dc, bool) or not isinstance(dc, int):
                raise world.WorldError(f"{dc!r} is not a difficulty class")
            modifier = arguments.get("modifier") or 0
            if isinstance(modifier, bool) or not isinstance(modifier, int):
                raise world.WorldError(f"{modifier!r} is not a modifier")

            outcome = ruleset.resolve(
                dc=dc, modifier=modifier, reason=arguments.get("reason", "")
            )
            database.add(
                Roll(
                    turn_id=turn_id,
                    notation=outcome.roll.notation,
                    dice=list(outcome.roll.dice),
                    modifier=outcome.roll.modifier,
                    total=outcome.roll.total,
                    reason=outcome.reason,
                    dc=outcome.dc,
                    degree=outcome.degree.value,
                )
            )
            await database.flush()
            return narration.Result(
                call,
                f"{character.name}'s {outcome.reason or 'check'} was a "
                f"{outcome.degree.value} ({outcome.roll.total} against {dc})",
            ), [
                _frame(
                    "roll",
                    {
                        "notation": outcome.roll.notation,
                        "dice": list(outcome.roll.dice),
                        "modifier": outcome.roll.modifier,
                        "total": outcome.roll.total,
                        "reason": outcome.reason,
                        "dc": outcome.dc,
                        "degree": outcome.degree.value,
                        "character": character.name,
                    },
                )
            ]

        if call.name == "move_party":
            place = arguments.get("place", "")
            return await moved(world.MOVED, {"place": place}, f"the party is at {place}")

        if call.name == "remember":
            key, value = arguments.get("key", ""), arguments.get("value", "")
            return await moved(
                world.REMEMBERED, {"key": key, "value": value}, f"{key} is {value}"
            )

        if call.name in ("damage", "heal"):
            character = _named(party, arguments.get("character", ""))
            amount = arguments.get("amount")
            kind = world.DAMAGED if call.name == "damage" else world.HEALED
            verb = "took" if call.name == "damage" else "recovered"
            return await moved(
                kind,
                {"character_id": str(character.id), "amount": amount},
                f"{character.name} {verb} {amount}",
            )

        if call.name in ("add_condition", "remove_condition"):
            character = _named(party, arguments.get("character", ""))
            condition = arguments.get("condition", "")
            kind = (
                world.AFFLICTED
                if call.name == "add_condition"
                else world.RELIEVED
            )
            became = "is" if call.name == "add_condition" else "is no longer"
            return await moved(
                kind,
                {"character_id": str(character.id), "condition": condition},
                f"{character.name} {became} {condition}",
            )

        if call.name == "pass_time":
            minutes = arguments.get("minutes")
            return await moved(
                world.ELAPSED, {"minutes": minutes}, f"{minutes} minutes passed"
            )

        raise world.WorldError(f"gary has no {call.name!r} to call")

    except (dice.DiceError, world.WorldError, systems.SystemError) as error:
        # Refused, not fatal. The narrator is told what went wrong and carries
        # on, and the player sees it — a tool that quietly did nothing would
        # leave the prose describing something that never happened.
        return narration.Result(call, str(error), failed=True), [
            _frame("error", {"detail": str(error), "code": "refused_tool"})
        ]


@router.post("/campaigns/{campaign_id}/turns")
async def take_turn(
    campaign_id: uuid.UUID, request: NewTurn, database: Db, user: CurrentUser
) -> StreamingResponse:
    """Say what you do, and have gary answer as it is generated.

    Everything that can be refused outright is refused here, before a byte is
    sent: no session, not your campaign, nothing said, nobody to play. Once
    the stream opens the status line is spent, so anything that goes wrong
    after that arrives as an event on it instead.
    """
    campaign = await _mine(database, user, campaign_id)

    party = list(
        await database.scalars(
            select(Character)
            .where(Character.campaign_id == campaign.id)
            .order_by(Character.created_at, Character.name)
        )
    )
    if not party:
        raise Refusal(
            status.HTTP_409_CONFLICT,
            "no_party",
            "There is nobody in this campaign to play yet",
        )

    gary = narration.narrator()
    said = gary.sanitise(request.message) or request.message

    player_turn = Turn(campaign_id=campaign.id, role="player", content=said)
    database.add(player_turn)
    await database.commit()

    return StreamingResponse(
        _stream(campaign.id, player_turn.id, request.message, gary),
        media_type="text/event-stream",
        # Whatever sits in front of this must not collect the whole body
        # before passing it on, or streaming is a stream-shaped hole.
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )


async def _stream(campaign_id, player_turn_id, message, gary):
    """The turn, as it happens.

    Opens its own session: this outlives the request handler, and the
    request-scoped one is closed the moment that returns.
    """
    factory = async_sessionmaker(db.engine, expire_on_commit=False)

    async with factory() as database:
        campaign = await database.get(Campaign, campaign_id)
        party = list(
            await database.scalars(
                select(Character)
                .where(Character.campaign_id == campaign_id)
                .order_by(Character.created_at, Character.name)
            )
        )
        turns = list(
            await database.scalars(
                select(Turn)
                .where(Turn.campaign_id == campaign_id)
                .order_by(Turn.created_at, Turn.id)
            )
        )

        ruleset = systems.ruleset(campaign.system_slug)
        module = systems.module(campaign.system_slug, campaign.module_slug)
        state = await world.of(database, campaign_id)

        prompt = narration.Prompt(
            briefing=ruleset.briefing(),
            system_slug=campaign.system_slug,
            module_slug=campaign.module_slug,
            module_title=module.title,
            module_premise=module.premise,
            world=world.render(state),
            message=message,
            transcript=[(turn.role, turn.content) for turn in turns],
        )

        gm_turn = Turn(campaign_id=campaign_id, role="gm", content="", complete=False)
        database.add(gm_turn)
        await database.flush()

        yield _frame("turn", {"turn_id": str(gm_turn.id), "role": "gm"})

        spoken: list[str] = []
        finished = False
        generator = gary.narrate(prompt)
        sending: list[narration.Result] | None = None

        try:
            while True:
                try:
                    event = await generator.asend(sending)
                except StopAsyncIteration:
                    finished = True
                    break

                sending = None

                if isinstance(event, narration.Said):
                    if event.text:
                        spoken.append(event.text)
                        yield _frame("narration", {"text": event.text})
                elif isinstance(event, narration.Calls):
                    results = []
                    for call in event.calls:
                        result, frames = await _run(
                            database, campaign, party, call, gm_turn.id
                        )
                        results.append(result)
                        for frame in frames:
                            yield frame
                    sending = results
                else:
                    # Refused. Not an error: gary declined, and that is an
                    # answer. No turn is kept, because nothing was narrated.
                    # An else rather than a third isinstance because the three
                    # are the whole union — a fourth arm would be a branch
                    # nothing can reach.
                    await database.delete(gm_turn)
                    await database.commit()
                    yield _frame(
                        "refusal", {"detail": event.detail, "code": "gm_refused"}
                    )
                    return

        except narration.NarrationError as error:
            logger.error("gm.unreachable", campaign_id=str(campaign_id))
            await database.delete(gm_turn)
            await database.commit()
            yield _frame(
                "error", {"detail": str(error), "code": "gm_unavailable"}
            )
            return

        finally:
            # Reached on a normal end and on the client walking away alike.
            # A turn cut off is kept and marked rather than dropped: the next
            # turn is told the transcript, and a hole in it is a story that
            # never happened.
            await generator.aclose()
            if spoken:
                gm_turn.content = "".join(spoken).strip()
                gm_turn.complete = finished
                await database.commit()
            else:
                await database.delete(gm_turn)
                await database.commit()

        yield _frame("done", {"turn_id": str(gm_turn.id), "role": "gm"})
