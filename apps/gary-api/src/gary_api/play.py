"""The catalogue, campaigns, the characters in them, and the world.

Everything here reaches its campaign first, and a campaign that is not yours
answers 404 rather than 403. A 403 would confirm it exists, and whether a
stranger has a campaign is not yours to learn.

Nothing in this module names a system. It asks the registry, which is what
lets a new system arrive as one file — see ``tests/test_pluggable.py``, which
fails the build if that stops being true.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from gary_api import systems, world
from gary_api.auth import CurrentUser, Db, Refusal
from gary_api.models import Campaign, Character, Turn

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
