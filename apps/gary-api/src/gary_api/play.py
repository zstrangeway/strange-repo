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

from gary_api import db, dice, logs, narration, scenes, systems, world
from gary_api.auth import CurrentUser, Db, Refusal
from gary_api.models import (
    Adversary,
    Campaign,
    Character,
    Roll,
    Scene,
    Turn,
    WorldEvent,
)

logger = logs.get_logger(__name__)

router = APIRouter(tags=["play"])

# Nothing here. What a character starts with, what an unarmoured one is worth
# hitting, what an unspecified swing does and which ability any of it comes
# off are all the system's to say — see gary_api.systems.base. A default kept
# here would be this module quietly holding a rule.


class ModuleResponse(BaseModel):
    slug: str
    title: str
    premise: str
    # Why anybody would go. A catalogue entry without one is a situation
    # nobody has been asked to do anything about.
    hook: str
    opening: str


class MethodResponse(BaseModel):
    slug: str
    name: str
    blurb: str
    # Whether gary produces the numbers, and whether you place them after.
    # Two questions and not one: rolling in order generates without arranging,
    # and typing them in arranges without generating.
    generates: bool
    arrange: bool


class SystemResponse(BaseModel):
    slug: str
    name: str
    blurb: str
    classes: list[str]
    abilities: list[str]
    degrees: list[str]
    # How this edition lets you arrive at six scores. Typing them in is always
    # last and always there.
    methods: list[MethodResponse]
    # Why, when a system generates nothing. Empty for the ones that do.
    cannot_generate: str
    # What a score may be, so a client can refuse a typo before sending it.
    scores: list[int]
    # What each score costs under this system's point buy, and the budget.
    # Empty when it has none. A client counts the spend; gary-api range-checks
    # what arrives, the same as it does for any other score.
    point_costs: dict[int, int]
    point_budget: int
    modules: list[ModuleResponse]


class ModelResponse(BaseModel):
    id: str
    name: str
    prompt_cost: float
    completion_cost: float
    context: int
    reasons: bool
    suggested: bool


class NewCampaign(BaseModel):
    name: str = Field(max_length=120)
    system: str = Field(max_length=64)
    module: str = Field(max_length=64)
    # Optional: naming no model is the common case, and the deployment's
    # default fills in.
    model: str | None = Field(default=None, max_length=128)

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
    # What the adventure is about, in the module's own words. Free, instant,
    # and true before gary has written anything — a situation on screen while
    # the opening is still arriving.
    premise: str
    # Why the party is here. On screen from the moment the page loads, so the
    # answer to "why am I here" is never only in gary's gift.
    hook: str
    # Where the module starts. The world holds this too, but a client should
    # not have to ask twice to render a campaign nobody has opened yet.
    place: str
    turns: int
    # Whether anybody has spoken. False means gary has not opened the scene,
    # which is what a client acts on rather than counting turns itself.
    begun: bool
    # Resolved, never null: a client should not have to know what the
    # deployment's default is to render which model a campaign runs on.
    model: str
    # Whether that came from the campaign or from the deployment, which is the
    # part a client does need to know to render "default" rather than a name.
    model_chosen: bool


class ChangeCampaign(BaseModel):
    """Null means hand it back to the deployment's default."""

    model: str | None = Field(default=None, max_length=128)


class NewCharacter(BaseModel):
    name: str = Field(max_length=80)
    character_class: str = Field(max_length=40)
    # Whether this is the one you play. False by default: a companion is what
    # a character is unless somebody says otherwise, and being the player is
    # the deliberate act.
    mine: bool = False
    level: int = Field(default=1, ge=1, le=30)
    # Null means "whatever the class and constitution come to", which is the
    # ordinary case. A number here is somebody importing a character that was
    # made elsewhere, and is taken at its word.
    max_hp: int | None = Field(default=None, ge=1, le=999)
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
    # As created, both of them. What somebody currently is comes off the world
    # — `GET /campaigns/{id}/world` — because a level is a fold over the log
    # the same way hit points are. This is the sheet, not the state.
    level: int
    experience: int
    max_hp: int
    abilities: dict[str, int]
    # "player" for the one you are, "gary" for the ones it speaks for.
    played_by: str


class MemberResponse(BaseModel):
    id: str
    name: str
    character_class: str
    level: int
    experience: int
    # What the next level costs, so a client can show how far along somebody
    # is without holding a copy of the table. None at the top, and in a system
    # that does not price a level at all — both are "there is no next number
    # to reach", which is the only thing a card can usefully say.
    next_level: int | None
    hp: int
    max_hp: int
    conditions: list[str]
    down: bool
    played_by: str


class FoeResponse(BaseModel):
    id: str
    name: str
    hp: int
    max_hp: int
    armour_class: int
    conditions: list[str]
    down: bool


class InOrder(BaseModel):
    id: str
    name: str
    side: str


class FightResponse(BaseModel):
    order: list[InOrder]
    # Where in the order it is, rather than who — a client rendering the list
    # wants to highlight a position, and the name is in the list already.
    at: int
    round: int


class WorldResponse(BaseModel):
    place: str
    minutes: int
    facts: dict[str, str]
    party: list[MemberResponse]
    # What the party has fought, still standing or not. Kept after a fight
    # ends because a monster that was killed is a fact about the campaign.
    enemies: list[FoeResponse]
    # Null when nobody is fighting, which is most of the time.
    fight: FightResponse | None


class EventResponse(BaseModel):
    seq: int
    kind: str
    payload: dict[str, Any]
    # Which scene it happened in. Null only for events older than scenes.
    scene_id: uuid.UUID | None


class TurnResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    complete: bool
    # Which scene it was said in, so a client can draw the seam where gary's
    # memory has one rather than showing an undivided scroll.
    scene_id: uuid.UUID
    rolls: list[dict[str, Any]]
    # What this turn changed, beside what it rolled. The stream carries both
    # as they happen; without this a reload would show the prose and lose
    # everything the engines did during it.
    changes: list[dict[str, Any]]


class SceneResponse(BaseModel):
    id: uuid.UUID
    number: int
    title: str
    # Null while a scene is being played, and also when it closed without gary
    # being reachable to say what happened. The two are told apart by whether
    # it is open.
    recap: str | None
    open: bool


class NewScene(BaseModel):
    title: str = Field(default="", max_length=160)


def _as_system(ruleset: systems.Ruleset) -> dict:
    return {
        "slug": ruleset.slug,
        "name": ruleset.name,
        "blurb": ruleset.blurb,
        "classes": list(ruleset.classes),
        "abilities": list(ruleset.abilities),
        "degrees": [degree.value for degree in ruleset.degrees],
        "methods": [
            {
                "slug": method.slug,
                "name": method.name,
                "blurb": method.blurb,
                "generates": method.generates,
                "arrange": method.arrange,
            }
            for method in ruleset.methods
        ],
        "cannot_generate": ruleset.cannot_generate,
        "scores": list(ruleset.scores),
        "point_costs": ruleset.point_costs,
        "point_budget": ruleset.point_budget,
        "modules": [
            {
                "slug": module.slug,
                "title": module.title,
                "premise": module.premise,
                "hook": module.hook,
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
        "premise": module.premise,
        "hook": module.hook,
        "place": module.opening,
        "turns": turns,
        "begun": turns > 0,
        "model": campaign.model or narration.models.default(),
        "model_chosen": campaign.model is not None,
    }


def _sheet_for(ruleset, wanted: dict[str, int] | None) -> dict[str, int]:
    """Six scores, checked against what this system has and allows.

    Nobody has to supply any: a campaign started before this existed has
    characters who never did, and not everybody wants to arrange six numbers
    before they can play. What is supplied has to be real.
    """
    sheet = {ability: ruleset.default_score for ability in ruleset.abilities}
    low, high = ruleset.scores

    for ability, score in (wanted or {}).items():
        if ability not in sheet:
            raise Refusal(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "no_such_ability",
                f"{ability!r} is not an ability in this system",
            )
        if isinstance(score, bool):
            # Pydantic guarantees an int by here, and is happy to make one out
            # of a boolean: an ability sent as `true` arrives as a score of 1.
            # Only this half needs saying, because only this half gets through.
            raise Refusal(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "bad_score",
                f"{score!r} is not a score",
            )
        if not low <= score <= high:
            raise Refusal(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "bad_score",
                f"a score in this system is between {low} and {high}",
            )
        sheet[ability] = score

    return sheet


def _starting_experience(ruleset, level: int) -> int:
    """What that level costs to reach, or nothing when the system cannot say.

    Nothing rather than a refusal: a system with no advancement table still
    makes characters, and add-1e refusing to price a level is not a reason to
    refuse to build one.
    """
    try:
        return ruleset.experience_for(level)
    except systems.SystemError:
        return 0


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


def _as_character(character: Character) -> dict:
    return {
        "id": character.id,
        "name": character.name,
        "character_class": character.character_class,
        "level": character.level,
        "experience": character.experience,
        "max_hp": character.max_hp,
        "abilities": character.abilities or {},
        "played_by": character.played_by,
    }


def _runnable(identifier: str | None) -> str | None:
    """Check a chosen model, or pass None straight through.

    The one rule: it has to be able to call tools. gary asks for a check and
    the rules grade it — a model that cannot call a tool would narrate a
    plausible game that nothing was adjudicating, which fails silently and is
    the worst kind available here.
    """
    if identifier is None:
        return None

    try:
        return narration.models.model(identifier).id
    except narration.models.ModelError as error:
        raise Refusal(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "unsupported_model", str(error)
        ) from error


def _gary_for(campaign: Campaign) -> narration.Narrator:
    """The narrator this campaign runs on, or a refusal saying why not.

    A deployment with no key is what a fresh app is until its secrets are set.
    Refused before a byte is sent, because this is one of the few things that
    can still be said with a status — after the stream opens it cannot — and
    because letting it escape reads as gary crashing rather than as gary not
    being configured.
    """
    try:
        return narration.narrator(campaign.model or narration.models.default())
    except narration.NarrationError as error:
        logger.error("gm.unconfigured", reason=str(error))
        raise Refusal(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "gm_unavailable",
            "gary cannot reach a model on this deployment",
        ) from error


async def _party(database, campaign_id: uuid.UUID) -> list[Character]:
    return list(
        await database.scalars(
            select(Character)
            .where(Character.campaign_id == campaign_id)
            .order_by(Character.created_at, Character.name)
        )
    )


def _playable(party: list[Character]) -> None:
    """Refuse a party there is nobody in for you to be.

    Two refusals rather than one, because they are two different problems and
    only one of them is fixed by making another character: an empty campaign
    needs anybody, a campaign of companions needs one of them to be you.
    """
    if not party:
        raise Refusal(
            status.HTTP_409_CONFLICT,
            "no_party",
            "There is nobody in this campaign to play yet",
        )
    if not any(character.played_by == "player" for character in party):
        raise Refusal(
            status.HTTP_409_CONFLICT,
            "no_character",
            "None of these characters is yours to play",
        )


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


@router.get("/models")
async def read_models() -> list[ModelResponse]:
    # No session, like the catalogue: what gary can be run on is part of
    # deciding whether to make an account.
    return [
        {
            "id": model.id,
            "name": model.name,
            "prompt_cost": model.prompt_cost,
            "completion_cost": model.completion_cost,
            "context": model.context,
            "reasons": model.reasons,
            "suggested": model.suggested,
        }
        for model in narration.models.available()
    ]


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
        model=_runnable(request.model),
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
    rows = list(
        await database.scalars(
            select(Campaign)
            .where(Campaign.user_id == user.id)
            .order_by(Campaign.created_at.desc())
        )
    )

    # Counted here rather than left at the default, which is what this did
    # before: every campaign in the list reported nought turns and none of
    # them had begun. One grouped query rather than one per campaign, because
    # this is the page signing in lands on.
    counted = dict(
        (
            await database.execute(
                select(Turn.campaign_id, func.count())
                .where(Turn.campaign_id.in_([campaign.id for campaign in rows]))
                .group_by(Turn.campaign_id)
            )
        ).all()
    ) if rows else {}

    return [
        _as_campaign(campaign, counted.get(campaign.id, 0)) for campaign in rows
    ]


@router.get("/campaigns/{campaign_id}")
async def read_campaign(
    campaign_id: uuid.UUID, database: Db, user: CurrentUser
) -> CampaignResponse:
    campaign = await _mine(database, user, campaign_id)
    turns = await database.scalar(
        select(func.count()).select_from(Turn).where(Turn.campaign_id == campaign.id)
    )
    return _as_campaign(campaign, turns or 0)


@router.patch("/campaigns/{campaign_id}")
async def change_campaign(
    campaign_id: uuid.UUID, request: ChangeCampaign, database: Db, user: CurrentUser
) -> CampaignResponse:
    """Move a campaign to another model, mid-game.

    Switching to something cheap while iterating and back for a session that
    matters is the whole reason the choice is exposed, so it cannot be a
    create-time decision.
    """
    campaign = await _mine(database, user, campaign_id)
    campaign.model = _runnable(request.model)
    await database.commit()

    turns = await database.scalar(
        select(func.count()).select_from(Turn).where(Turn.campaign_id == campaign.id)
    )
    return _as_campaign(campaign, turns or 0)


class WantScores(BaseModel):
    method: str = Field(max_length=64)


class ScoreResponse(BaseModel):
    score: int
    # The dice that made it, kept rather than summed away: "15" and "6, 5, 4
    # and a discarded 1" are different things to read while you decide where
    # to put it. Empty for a method that throws none.
    dice: list[int]
    dropped: int | None


class ScoresResponse(BaseModel):
    method: str
    scores: list[ScoreResponse]
    # Which ability each is already against, when the method places them for
    # you. Null when they are yours to arrange.
    assigned: dict[str, int] | None


@router.post("/campaigns/{campaign_id}/scores")
async def roll_scores(
    campaign_id: uuid.UUID, request: WantScores, database: Db, user: CurrentUser
) -> ScoresResponse:
    """Six scores, by a method this system offers.

    gary-api's dice and not the browser's, for the reason they are not the
    model's either: a number a client sent is a number somebody typed.

    Nothing is stored. A set nobody made a character out of is not a fact
    about the campaign, which is also why re-rolling is not refused — it costs
    nothing that matters, and refusing would only make people delete the
    character and start again.
    """
    campaign = await _mine(database, user, campaign_id)
    ruleset = systems.ruleset(campaign.system_slug)

    try:
        wanted = ruleset.method(request.method)
        thrown = ruleset.generate(request.method)
    except systems.SystemError as error:
        raise Refusal(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "no_such_method", str(error)
        ) from error

    return {
        "method": wanted.slug,
        "scores": thrown,
        # Placed already, when the method does not let you arrange them —
        # three dice straight down the page is the whole of first edition's
        # character creation and there is nothing left to decide.
        "assigned": (
            None
            if wanted.arrange
            else dict(
                zip(ruleset.abilities, [one["score"] for one in thrown], strict=True)
            )
        ),
    }


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

    if request.mine:
        already = await database.scalar(
            select(func.count())
            .select_from(Character)
            .where(
                Character.campaign_id == campaign.id,
                Character.played_by == "player",
            )
        )
        if already:
            # One is the whole idea. Two would put somebody back to playing
            # the party rather than a person in it — and take over is how you
            # change your mind, so this is not a state anybody needs.
            raise Refusal(
                status.HTTP_409_CONFLICT,
                "already_playing",
                "You are already playing somebody in this campaign",
            )

    ruleset = systems.ruleset(campaign.system_slug)
    abilities = _sheet_for(ruleset, request.abilities)

    character = Character(
        campaign_id=campaign.id,
        name=request.name,
        character_class=spelled,
        level=request.level,
        # The class's hit die plus what their constitution is worth. Asked of
        # the ruleset rather than worked out here, because it is a rule — and
        # a system with no hit dice typed in yet says so by handing back its
        # own default rather than by being special-cased.
        max_hp=(
            request.max_hp
            if request.max_hp is not None
            else ruleset.hit_points(spelled, abilities)
        ),
        # Where that level starts, so being made at level 3 and earning your
        # way to 3 are the same character afterwards. A system that does not
        # price a level leaves this at nothing, which is what every character
        # made before any of this existed has.
        experience=_starting_experience(ruleset, request.level),
        abilities=abilities,
        played_by="player" if request.mine else "gary",
    )
    database.add(character)
    await database.commit()

    return _as_character(character)


@router.get("/campaigns/{campaign_id}/characters")
async def read_party(
    campaign_id: uuid.UUID, database: Db, user: CurrentUser
) -> list[CharacterResponse]:
    campaign = await _mine(database, user, campaign_id)
    return [
        _as_character(character)
        for character in await _party(database, campaign.id)
    ]


@router.post("/campaigns/{campaign_id}/characters/{character_id}/player")
async def take_over(
    campaign_id: uuid.UUID,
    character_id: uuid.UUID,
    database: Db,
    user: CurrentUser,
) -> list[CharacterResponse]:
    """Play this one instead, and hand whoever it was to gary.

    The whole party comes back rather than the one character, because two of
    them changed and a client that had to work out the other from an absence
    would sometimes get it wrong.
    """
    campaign = await _mine(database, user, campaign_id)
    party = await _party(database, campaign.id)

    wanted = next(
        (one for one in party if one.id == character_id),
        None,
    )
    if wanted is None:
        raise Refusal(
            status.HTTP_404_NOT_FOUND,
            "no_such_character",
            "No such character in this campaign",
        )

    for character in party:
        character.played_by = "player" if character is wanted else "gary"
    await database.commit()

    return [_as_character(character) for character in party]


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


def _as_change(event: WorldEvent, named: dict[str, str]) -> dict:
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


@router.get("/campaigns/{campaign_id}/turns")
async def read_transcript(
    campaign_id: uuid.UUID, database: Db, user: CurrentUser
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


def _as_scene(scene: Scene) -> dict:
    return {
        "id": scene.id,
        "number": scene.number,
        "title": scene.title,
        "recap": scene.recap,
        "open": scene.closed_at is None,
    }


@router.get("/campaigns/{campaign_id}/scenes")
async def read_scenes(
    campaign_id: uuid.UUID, database: Db, user: CurrentUser
) -> list[SceneResponse]:
    """Every scene, oldest first, with what each is remembered by."""
    campaign = await _mine(database, user, campaign_id)
    # Reading opens the first scene if there is not one yet, which is the same
    # answer a campaign gives to its first turn — a campaign is always in a
    # scene, and it would be odd for looking to be the thing that decides.
    await scenes.current(database, campaign.id)
    await database.commit()
    return [_as_scene(scene) for scene in await scenes.all_of(database, campaign.id)]


@router.post(
    "/campaigns/{campaign_id}/scenes", status_code=status.HTTP_201_CREATED
)
async def begin_scene(
    campaign_id: uuid.UUID, request: NewScene, database: Db, user: CurrentUser
) -> SceneResponse:
    """End the scene being played and start the next one.

    Closing runs the reconciliation pass, so this can take as long as a model
    takes — it is the one request here that is slow on purpose.
    """
    campaign = await _mine(database, user, campaign_id)

    # Same refusals as playing, for the same reason: a scene is a stretch of
    # play, and there is nobody to play it.
    party = await _party(database, campaign.id)
    _playable(party)

    opened = await scenes.begin(database, campaign, party, _run, request.title)
    await database.commit()
    return _as_scene(opened)


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
        {
            "seq": event.seq,
            "kind": event.kind,
            "payload": event.payload or {},
            "scene_id": event.scene_id,
        }
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


def _text_of(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise world.WorldError(f"an adversary needs a {key}")
    return value.strip()


def _count_of(payload: dict, key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise world.WorldError(f"an adversary's {key} must be a whole number")
    return value


async def _either_side(database, campaign, party, name: str):
    """That name, whichever side it is on, and which column holds it."""
    try:
        return "character_id", _named(party, name)
    except world.WorldError:
        pass

    wanted = (name or "").strip().lower()
    for adversary in await database.scalars(
        select(Adversary).where(Adversary.campaign_id == campaign.id)
    ):
        if adversary.name.lower() == wanted:
            return "adversary_id", adversary
    raise world.WorldError(f"nobody here is called {name!r}")


def _in_fight(state: world.World, name: str):
    """Whoever that is, on either side, by the name a person would use."""
    wanted = (name or "").strip().lower()
    for candidate in [*state.party, *state.enemies]:
        if candidate.name.lower() == wanted:
            return candidate
    raise world.WorldError(f"nobody in this fight is called {name!r}")


async def _fighting(
    database, campaign, party, foes, call, arguments, rolled, moved, turn_id
):
    """The four things that can happen to a fight.

    Together rather than spread through the chain in ``_run``, because every
    one of them needs the same two things first — the world as it stands, and
    whether there is a fight at all — and because they are one feature.

    What gary decides here: who is fighting, and what somebody tries. What it
    does not: who goes first, whether a blow lands, or what it costs.
    """
    ruleset = systems.ruleset(campaign.system_slug)
    state = await world.of(database, campaign.id)
    fight = state.fight
    rows = {str(one.id): one for one in [*party, *foes]}

    if call.name == "begin_combat":
        if fight is not None:
            raise world.WorldError("a fight is already happening")
        # No check that anybody is here to fight it: the turn endpoint refuses
        # a campaign with no party before a byte is streamed, so a fight
        # cannot be started in one. A guard here would be a branch nothing
        # could reach.

        wanted = arguments.get("adversaries") or []
        if not isinstance(wanted, list) or not wanted:
            raise world.WorldError("a fight needs something to fight")

        made = []
        for one in wanted:
            if not isinstance(one, dict):
                raise world.WorldError("each adversary needs a name and a shape")
            adversary = Adversary(
                campaign_id=campaign.id,
                name=_text_of(one, "name")[:80],
                max_hp=_count_of(one, "hit_points"),
                armour_class=_count_of(one, "armour_class"),
                attack_bonus=int(one.get("attack_bonus") or 0),
                damage=str(one.get("damage") or ruleset.unarmed_damage)[:32],
            )
            database.add(adversary)
            made.append(adversary)
        await database.flush()

        # Everybody rolls and the engine sorts them. This is the whole point:
        # gary decided the order before, with modifiers it invented.
        frames, order = [], []
        for character in party:
            score = (character.abilities or {}).get(ruleset.initiative_ability, 10)
            thrown = ruleset.initiative(ruleset.modifier(score))
            frames.append(
                _frame(
                    "roll",
                    rolled(thrown, character, ability=ruleset.initiative_ability),
                )
            )
            order.append((thrown.total, str(character.id), character.name))
        for adversary in made:
            thrown = ruleset.initiative(adversary.attack_bonus)
            frames.append(_frame("roll", rolled(thrown, foe=adversary)))
            order.append((thrown.total, str(adversary.id), adversary.name))

        # Highest first, ties broken by name so that folding the log twice
        # lands the same way twice.
        order.sort(key=lambda one: (-one[0], one[2]))
        result, changed = await moved(
            world.FOUGHT,
            {"order": [one[1] for one in order]},
            "a fight began. The order is "
            + ", ".join(f"{name} ({total})" for total, _, name in order),
        )
        return result, [*frames, *changed]

    if fight is None:
        raise world.WorldError("there is no fight happening")

    up = state.anyone(fight.whose)

    if call.name == "end_combat":
        return await moved(world.PEACE, {}, "the fight is over")

    if call.name == "end_turn":
        if isinstance(up, world.Member) and up.played_by == "player":
            # The reason combat was asked for. Gary reaching the player's turn
            # has to stop there and ask, not narrate through it.
            #
            # Once they have taken it, though, somebody has to move the order
            # on — and it is gary, because the player says what they do rather
            # than operating the machinery. So the bar is that they acted, not
            # that gary may never do this: a fight where nothing could end the
            # player's turn would stop on it forever.
            raise world.WorldError(
                f"it is {up.name}'s turn, and {up.name} is the player's to "
                "take — ask them what they do"
            )
        return await moved(
            world.TURNED, {}, f"{up.name if up else 'that'}'s turn is over"
        )

    # An attack, then. Whoever is up swings at somebody.
    attacker = _in_fight(state, arguments.get("attacker", ""))
    if up is None or attacker.id != up.id:
        raise world.WorldError(
            f"it is not {attacker.name}'s turn — it is "
            f"{up.name if up else 'nobody'}'s"
        )
    target = _in_fight(state, arguments.get("target", ""))
    if target.id == attacker.id:
        raise world.WorldError(f"{attacker.name} cannot attack themselves")
    if target.down:
        raise world.WorldError(f"{target.name} is already down")

    swinging = rows.get(attacker.id)
    hitting = isinstance(attacker, world.Foe)
    bonus = (
        attacker.attack_bonus
        if hitting
        else ruleset.attack_bonus(swinging.abilities)
    )
    guard = (
        target.armour_class
        if isinstance(target, world.Foe)
        else ruleset.default_armour_class
    )
    swing = ruleset.resolve(
        dc=guard, modifier=bonus, reason=f"attack on {target.name}"
    )

    mine = {"foe": swinging} if hitting else {"who": swinging}
    frames = [_frame("roll", rolled(swing.roll, graded=swing, **mine))]

    landed = swing.degree in (
        systems.Degree.SUCCESS,
        systems.Degree.CRITICAL_SUCCESS,
    )

    said = f"{attacker.name} missed {target.name}"
    if landed:
        hurt = dice.roll(
            attacker.damage if hitting else ruleset.unarmed_damage,
            f"{attacker.name} hits {target.name}",
        )
        frames.append(_frame("roll", rolled(hurt, **mine)))
        whose = "adversary_id" if isinstance(target, world.Foe) else "character_id"
        _, changed = await moved(
            world.DAMAGED,
            {whose: target.id, "amount": hurt.total},
            "",
        )
        frames.extend(changed)
        said = f"{attacker.name} hit {target.name} for {hurt.total}"

    # Swinging is what taking a turn *is* here — a turn holds one action and
    # nothing else is modelled — so the order moves on by itself. Which is
    # also how the player's turn ever ends: gary may not end it for them, and
    # a fight that could not move past them would stop there forever.
    _, over = await moved(world.TURNED, {}, "")
    return narration.Result(
        call, f"{said} ({swing.roll.total} against {guard}). Their turn is over."
    ), [*frames, *over]


async def _run(
    database,
    campaign: Campaign,
    party: list[Character],
    call,
    turn_id: uuid.UUID | None,
    scene_id: uuid.UUID,
) -> tuple[narration.Result, list[str]]:
    """Do what the narrator asked, or refuse it, and say what came of it.

    Everything a narrator can change goes through here, which is the whole
    arrangement: the model proposes, the engines decide, and what goes back to
    the model is what actually happened rather than what it suggested.
    """
    arguments = call.arguments or {}

    async def moved(kind: str, payload: dict, summary: str):
        await world.record(database, campaign.id, kind, payload, turn_id, scene_id)
        return narration.Result(call, summary), [
            _frame("world", {"kind": kind, **payload})
        ]

    def rolled(made, who=None, graded=None, ability=None, foe=None) -> dict:
        """Write one roll down and describe it, whoever it belonged to.

        One place, so what is stored and what is streamed cannot drift: the
        frame said who made a check long before the row had anywhere to keep
        it, and a reload lost the name every time.

        ``who`` is a character row and ``foe`` an adversary row; at most one.
        Rows rather than the world's projection of them, because what goes in
        the column is an id the database will check.
        """
        reason = graded.reason if graded else made.reason
        named = foe or who
        database.add(
            Roll(
                turn_id=turn_id,
                character_id=who.id if who else None,
                adversary_id=foe.id if foe else None,
                notation=made.notation,
                dice=list(made.dice),
                modifier=made.modifier,
                ability=ability,
                total=made.total,
                reason=reason,
                dc=graded.dc if graded else None,
                degree=graded.degree.value if graded else None,
            )
        )
        described = {
            "notation": made.notation,
            "dice": list(made.dice),
            "modifier": made.modifier,
            "total": made.total,
            "reason": reason,
            # Named rather than identified: everything downstream of this is
            # something a person reads.
            "character": named.name if named else None,
            "ability": ability,
            # So a card can tell a monster's roll from a party member's
            # without having to know every name at the table.
            "side": "adversary" if foe else "party",
        }
        if graded:
            described["dc"] = graded.dc
            described["degree"] = graded.degree.value
        return described

    try:
        if call.name == "roll":
            # Whose it is, when it is anybody's. A roll about how sound the
            # timbers are belongs to nobody, and saying otherwise would be
            # inventing a fact to fill a field.
            named = (arguments.get("character") or "").strip()
            who = _named(party, named) if named else None
            notation = arguments.get("notation", "")

            ability = (arguments.get("ability") or "").strip().lower() or None
            modifier = 0
            if who is not None:
                # Plain dice for a person's roll. This is the hole everything
                # in `check` was built to close, left open: gary ran a whole
                # encounter through it, giving four characters initiative
                # modifiers of +1, +2, +3 and +4 that came from nowhere, off
                # sheets of straight tens. A rule that binds only the tool
                # gary can route around is not a rule.
                if dice.modifier_in(notation):
                    raise world.WorldError(
                        f"{notation!r} carries a modifier, and a roll for "
                        f"{who.name} takes plain dice — name an ability and "
                        "the sheet decides what it is worth"
                    )
                ruleset = systems.ruleset(campaign.system_slug)
                if ability:
                    if ability not in ruleset.abilities:
                        raise world.WorldError(
                            f"{ability!r} is not an ability in this system"
                        )
                    modifier = ruleset.modifier(
                        (who.abilities or {}).get(ability, 10)
                    )
                    notation = f"{notation}{modifier:+d}" if modifier else notation

            made = dice.roll(notation, arguments.get("reason", ""))
            payload = rolled(made, who, ability=ability)
            await database.flush()
            return narration.Result(
                call,
                f"{made.notation} came up {made.total}"
                + (f" for {who.name}" if who else ""),
            ), [_frame("roll", payload)]

        if call.name == "check":
            # The rules grade it, not gary and not this module. A system with
            # four degrees returns four here without anything else changing.
            ruleset = systems.ruleset(campaign.system_slug)

            # Everyone facing the same thing, in one call. Resolved before
            # anything is rolled, because a check is all or nothing: half of
            # it applied says two of them crossed and the fiction says they
            # went together.
            names = arguments.get("characters") or []
            if isinstance(names, str):
                names = [names]
            if not names:
                raise world.WorldError("a check needs somebody to make it")
            facing = [_named(party, str(name)) for name in names]

            dc = arguments.get("dc")
            if isinstance(dc, bool) or not isinstance(dc, int):
                raise world.WorldError(f"{dc!r} is not a difficulty class")

            # An ability, not a modifier. What a score is worth is a rule the
            # ruleset owns, and the score itself is on a sheet the narrator
            # does not — which is why gary is never asked for the number.
            ability = (arguments.get("ability") or "").strip().lower() or None
            if ability and ability not in ruleset.abilities:
                raise world.WorldError(
                    f"{ability!r} is not an ability in this system"
                )

            reason = arguments.get("reason", "")
            said, frames = [], []
            for character in facing:
                modifier = (
                    ruleset.modifier((character.abilities or {}).get(ability, 10))
                    if ability
                    else 0
                )
                outcome = ruleset.resolve(dc=dc, modifier=modifier, reason=reason)
                frames.append(
                    _frame("roll", rolled(outcome.roll, character, outcome, ability))
                )
                said.append(
                    f"{character.name}'s {outcome.reason or 'check'} was a "
                    f"{outcome.degree.value} "
                    f"({outcome.roll.total} against {outcome.dc})"
                )

            await database.flush()
            # One summary covering all of them, because one call asked. A
            # model told only about the last of four would narrate the other
            # three from memory.
            return narration.Result(call, "; ".join(said)), frames

        if call.name in ("begin_combat", "attack", "end_turn", "end_combat"):
            foes = list(
                await database.scalars(
                    select(Adversary).where(Adversary.campaign_id == campaign.id)
                )
            )
            return await _fighting(
                database,
                campaign,
                party,
                foes,
                call,
                arguments,
                rolled,
                moved,
                turn_id,
            )

        if call.name == "move_party":
            place = arguments.get("place", "")
            return await moved(world.MOVED, {"place": place}, f"the party is at {place}")

        if call.name == "remember":
            key, value = arguments.get("key", ""), arguments.get("value", "")
            return await moved(
                world.REMEMBERED, {"key": key, "value": value}, f"{key} is {value}"
            )

        if call.name in ("damage", "heal"):
            # Either side. A monster takes hit points off the same way a
            # character does, and a tool that only reached the party would
            # send gary back to narrating a wound nothing recorded.
            whose, character = await _either_side(
                database, campaign, party, arguments.get("character", "")
            )
            amount = arguments.get("amount")
            kind = world.DAMAGED if call.name == "damage" else world.HEALED
            verb = "took" if call.name == "damage" else "recovered"
            return await moved(
                kind,
                {whose: str(character.id), "amount": amount},
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

        if call.name == "award_experience":
            ruleset = systems.ruleset(campaign.system_slug)

            # All of them or none, for the check's reason: a party survives a
            # thing together, and half an award applied says two of them were
            # there for something all four came through.
            names = arguments.get("awarded") or []
            if isinstance(names, str):
                names = [names]
            if not names:
                raise world.WorldError("an award needs somebody to give it to")
            earning = [_named(party, str(name)) for name in names]

            amount = arguments.get("experience")
            if isinstance(amount, bool) or not isinstance(amount, int):
                raise world.WorldError(f"{amount!r} is not an amount of experience")
            reason = arguments.get("reason", "")

            # Folded once, before anything is written. Where somebody stands
            # is the sheet plus what the log did to it, never the row — the
            # row is where they started and nothing ever writes it again.
            folded = {
                one.id: one for one in (await world.of(database, campaign.id)).party
            }
            said, frames = [], []
            for character in earning:
                # A lookup rather than a search: `_named` already found them
                # in the party and the fold is built from that same party, so
                # a miss here is impossible and a branch guarding it would be
                # one nothing could ever take.
                standing = folded[str(character.id)]

                # The bound, before anything is written. Damage is bounded by
                # a fight and experience by nothing, so without this a model
                # having a strange turn could hand out ten thousand and jump
                # four levels in a sentence.
                most = ruleset.most_per_award(standing.level)
                if amount > most:
                    raise world.WorldError(
                        f"{amount} is more experience than this system allows "
                        f"in one award at level {standing.level}; the most is "
                        f"{most}"
                    )

                await world.record(
                    database,
                    campaign.id,
                    world.EARNED,
                    {
                        "character_id": str(character.id),
                        "amount": amount,
                        "reason": reason,
                    },
                    turn_id,
                    scene_id,
                )
                frames.append(
                    _frame(
                        "world",
                        {
                            "kind": world.EARNED,
                            "character": character.name,
                            "amount": amount,
                            "reason": reason,
                        },
                    )
                )
                total = standing.experience + amount
                said.append(
                    f"{character.name} gained {amount} experience"
                    f"{f' for {reason}' if reason else ''} and is on {total}"
                )

                # Gary proposed the award; everything below is the engine's
                # answer to it, which is why it is a second event rather than
                # a field on the first one.
                for reached in range(
                    standing.level + 1, ruleset.level_at(total) + 1
                ):
                    gained = ruleset.gains(
                        character.character_class, character.abilities or {}
                    )
                    await world.record(
                        database,
                        campaign.id,
                        world.LEVELLED,
                        {
                            "character_id": str(character.id),
                            "level": reached,
                            "hit_points": gained,
                        },
                        turn_id,
                        scene_id,
                    )
                    frames.append(
                        _frame(
                            "world",
                            {
                                "kind": world.LEVELLED,
                                "character": character.name,
                                "level": reached,
                                "hit_points": gained,
                            },
                        )
                    )
                    said.append(
                        f"{character.name} reached level {reached} "
                        f"and gained {gained} hit points"
                    )

            await database.flush()
            return narration.Result(call, "; ".join(said)), frames

        if call.name == "pass_time":
            minutes = arguments.get("minutes")
            return await moved(
                world.ELAPSED, {"minutes": minutes}, f"{minutes} minutes passed"
            )

        if call.name == "scene":
            # Noted, not acted on. A boundary inside a turn would leave that
            # turn's narration half in each scene, and the close pass would
            # run inside a stream that is still open. The turn that ends a
            # scene is the last turn of it.
            title = arguments.get("title", "")
            return narration.Result(
                call, f"the scene will change to {title!r} when this turn ends"
            ), []

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

    party = await _party(database, campaign.id)
    _playable(party)

    gary = _gary_for(campaign)

    said = gary.sanitise(request.message) or request.message

    # A scene that has outgrown what may be sent every turn is broken here,
    # before the turn joins it, rather than after — so this turn starts the
    # new scene rather than being the straw that ended the old one. The bound
    # is applied whether or not gary ever asks for a break, which is the only
    # way a bound means anything.
    scene = await scenes.current(database, campaign.id)
    if await scenes.outgrown(database, scene):
        scene = await scenes.begin(database, campaign, party, _run)

    player_turn = Turn(
        campaign_id=campaign.id, scene_id=scene.id, role="player", content=said
    )
    database.add(player_turn)
    await database.commit()

    return StreamingResponse(
        _stream(campaign.id, scene.id, request.message, gary),
        media_type="text/event-stream",
        # Whatever sits in front of this must not collect the whole body
        # before passing it on, or streaming is a stream-shaped hole.
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )


# What gary is asked for when a campaign has a party and nothing has been
# said. Not a player's message — there is no player message, and that is the
# only thing unusual about an opening — but it arrives by the same route,
# because everything else about it is an ordinary turn.
OPENING = (
    "Open the campaign. Nothing has happened yet and nobody has said "
    "anything.\n\n"
    "Put the party in the situation, not in front of it. In two or three "
    "short paragraphs: say plainly why they are here and who wants this "
    "dealt with — you were told, so tell them — then show them the thing "
    "that is wrong, happening now, close enough to touch.\n\n"
    "End on pressure: something that has just changed, or is about to, and "
    "that they will have to answer. Give them a way in they can take this "
    "minute, not a landscape to admire. Do not end by asking what they do; "
    "they know, and they will tell you."
)


@router.post("/campaigns/{campaign_id}/opening")
async def begin_campaign(
    campaign_id: uuid.UUID, database: Db, user: CurrentUser
) -> StreamingResponse:
    """Have gary set the scene, once there is somebody to set it for.

    A campaign with a party and nothing said is a table where everyone has sat
    down and nobody has spoken. Somebody has to speak first, and it is not the
    player.
    """
    campaign = await _mine(database, user, campaign_id)

    party = await _party(database, campaign.id)
    _playable(party)

    said = await database.scalar(
        select(func.count()).select_from(Turn).where(Turn.campaign_id == campaign.id)
    )
    if said:
        # Refused here rather than left to the client to avoid, because a
        # reload and a second tab both reach this and neither knows about the
        # other. Two openings would be two beginnings, and the second narrated
        # to a table that had already started.
        raise Refusal(
            status.HTTP_409_CONFLICT,
            "already_begun",
            "This campaign has already begun",
        )

    gary = _gary_for(campaign)

    scene = await scenes.current(database, campaign.id)
    await database.commit()

    return StreamingResponse(
        _stream(campaign.id, scene.id, OPENING, gary),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )


async def _left_a_mark(database, turn_id: uuid.UUID) -> bool:
    """Did this turn change anything that outlives it?

    Asked of the database rather than tracked in a variable, because what
    matters is what was actually written — a tool the engines refused looks
    exactly like a tool that ran, right up until you go looking for the row.
    """
    rolled = await database.scalar(
        select(func.count()).select_from(Roll).where(Roll.turn_id == turn_id)
    )
    changed = await database.scalar(
        select(func.count())
        .select_from(WorldEvent)
        .where(WorldEvent.turn_id == turn_id)
    )
    return bool(rolled or changed)


async def _stream(campaign_id, scene_id, message, gary):
    """The turn, as it happens.

    Opens its own session: this outlives the request handler, and the
    request-scoped one is closed the moment that returns.
    """
    factory = async_sessionmaker(db.engine, expire_on_commit=False)

    async with factory() as database:
        campaign = await database.get(Campaign, campaign_id)
        party = await _party(database, campaign_id)
        # This scene's turns, not the campaign's. Prose stops being memory at
        # a scene boundary; what crosses one is the world and the recaps.
        scene = await database.get(Scene, scene_id)
        turns = await scenes.turns_in(database, scene_id)

        ruleset = systems.ruleset(campaign.system_slug)
        module = systems.module(campaign.system_slug, campaign.module_slug)
        state = await world.of(database, campaign_id)

        prompt = narration.Prompt(
            briefing=ruleset.briefing(),
            model=campaign.model or narration.models.default(),
            system_slug=campaign.system_slug,
            module_slug=campaign.module_slug,
            module_title=module.title,
            module_premise=module.premise,
            module_hook=module.hook,
            world=world.render(state),
            message=message,
            transcript=[(turn.role, turn.content) for turn in turns],
            scene_title=scene.title,
            recaps=await scenes.recaps(database, campaign_id),
        )

        gm_turn = Turn(
            campaign_id=campaign_id,
            scene_id=scene_id,
            role="gm",
            content="",
            complete=False,
        )
        database.add(gm_turn)
        await database.flush()

        yield _frame("turn", {"turn_id": str(gm_turn.id), "role": "gm"})

        spoken: list[str] = []
        finished = False
        wanted_scene: str | None = None
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
                            database, campaign, party, call, gm_turn.id, scene_id
                        )
                        if call.name == "scene":
                            # Acted on once the stream is done, not here.
                            wanted_scene = call.arguments.get("title", "")
                        results.append(result)
                        for frame in frames:
                            yield frame
                    sending = results
                else:
                    # Refused. Not an error: gary declined, and that is an
                    # answer. An else rather than a third isinstance because
                    # the three are the whole union — a fourth arm would be a
                    # branch nothing can reach.
                    #
                    # Whether the turn survives is decided in one place, below,
                    # on whether it did anything. A decline that changed
                    # nothing leaves nothing behind; a decline that came after
                    # the dice were already thrown is not nothing.
                    yield _frame(
                        "refusal", {"detail": event.detail, "code": "gm_refused"}
                    )
                    return

        except narration.NarrationError as error:
            logger.error("gm.unreachable", campaign_id=str(campaign_id))
            yield _frame(
                "error", {"detail": str(error), "code": "gm_unavailable"}
            )
            return

        finally:
            # Reached on a normal end, on a refusal, on an unreachable model
            # and on the client walking away alike — which is why the decision
            # about what to keep is only made here.
            #
            # A turn cut off is kept and marked rather than dropped: the next
            # turn is told the transcript, and a hole in it is a story that
            # never happened.
            await generator.aclose()
            if spoken:
                gm_turn.content = "".join(spoken).strip()
                gm_turn.complete = finished
                await database.commit()
            elif await _left_a_mark(database, gm_turn.id):
                # Silence is not nothing. Gary can spend a whole turn calling
                # tools and never reach a word of prose — and deleting that
                # turn takes its rolls with it, because they cascade, while
                # leaving the damage it dealt behind, because world events do
                # not. What that produces is a transcript in which nothing
                # happened beside a party that is bleeding, and no way to ever
                # find out why.
                gm_turn.content = ""
                gm_turn.complete = False
                await database.commit()
            else:
                await database.delete(gm_turn)
                await database.commit()

        # Now the turn is over, and only now. Closing a scene runs a whole
        # second pass through a model, and doing that mid-stream would stall
        # the narration the player is reading.
        if wanted_scene is not None:
            opened = await scenes.begin(
                database, campaign, party, _run, wanted_scene
            )
            await database.commit()
            yield _frame(
                "scene",
                {"scene_id": str(opened.id), "title": opened.title,
                 "number": opened.number},
            )

        yield _frame("done", {"turn_id": str(gm_turn.id), "role": "gm"})
