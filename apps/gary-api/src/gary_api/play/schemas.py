"""Request and response schemas for the play API."""

import uuid
from typing import Any

from pydantic import BaseModel, Field, field_validator

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
    # And whether it spends the system's budget, which is the third: those two
    # answer the same for point buy and for typing them in, and a client left
    # to tell them apart by slug is a client keeping its own copy of the rules.
    spends: bool


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

class NewTurn(BaseModel):
    message: str = Field(max_length=4000)

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Say something")
        return cleaned
