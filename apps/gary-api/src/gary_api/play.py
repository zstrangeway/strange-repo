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
from gary_api.models import Campaign, Character, Roll, Scene, Turn

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
        "premise": module.premise,
        "place": module.opening,
        "turns": turns,
        "begun": turns > 0,
        "model": campaign.model or narration.models.default(),
        "model_chosen": campaign.model is not None,
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
                }
                for roll in turn.rolls
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

    party = list(
        await database.scalars(
            select(Character)
            .where(Character.campaign_id == campaign.id)
            .order_by(Character.created_at, Character.name)
        )
    )
    if not party:
        # Same refusal as playing, for the same reason: a scene is a stretch
        # of play, and there is nobody to play.
        raise Refusal(
            status.HTTP_409_CONFLICT,
            "no_party",
            "There is nobody in this campaign to play yet",
        )

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
    "Open the scene. The party has just arrived and nothing has happened yet. "
    "Set the situation: where they are, what they can see and hear, and what "
    "is immediately in front of them. Address the players as 'you' and give "
    "them something worth reacting to. Do not ask them what they do — the "
    "scene should make that obvious."
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


async def _stream(campaign_id, scene_id, message, gary):
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
