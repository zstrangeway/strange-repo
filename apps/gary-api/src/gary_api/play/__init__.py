"""Backward-compatible public surface for ``gary_api.play``.

Importing the route modules registers their handlers on ``router``.  The
names below are the ones callers and tests already reached for.
"""

from gary_api.play import catalogue, campaigns, engine, world_read
from gary_api.play.router import router

# Backward-compatible names used by callers and tests.
from gary_api.play.campaigns import (
    _sheet_for,
    add_character,
    change_campaign,
    list_campaigns,
    read_campaign,
    read_party,
    roll_scores,
    start_campaign,
    take_over,
)
from gary_api.play.catalogue import read_catalogue, read_models, read_system
from gary_api.play.engine import OPENING, _run, begin_campaign, take_turn
from gary_api.play.schemas import (
    CampaignResponse,
    ChangeCampaign,
    CharacterResponse,
    EventResponse,
    FightResponse,
    FoeResponse,
    InOrder,
    MemberResponse,
    MethodResponse,
    ModelResponse,
    ModuleResponse,
    NewCampaign,
    NewCharacter,
    NewScene,
    NewTurn,
    SceneResponse,
    ScoreResponse,
    ScoresResponse,
    SystemResponse,
    TurnResponse,
    WantScores,
    WorldResponse,
)
from gary_api.play.world_read import (
    begin_scene,
    read_history,
    read_scenes,
    read_transcript,
    read_world,
)

__all__ = [
    "router",
    "OPENING",
    "take_turn",
    "begin_campaign",
    "_run",
    "_sheet_for",
    "read_catalogue",
    "read_system",
    "read_models",
    "start_campaign",
    "list_campaigns",
    "read_campaign",
    "change_campaign",
    "roll_scores",
    "add_character",
    "read_party",
    "take_over",
    "read_world",
    "read_transcript",
    "read_scenes",
    "begin_scene",
    "read_history",
    "CampaignResponse",
    "ChangeCampaign",
    "CharacterResponse",
    "EventResponse",
    "FightResponse",
    "FoeResponse",
    "InOrder",
    "MemberResponse",
    "MethodResponse",
    "ModelResponse",
    "ModuleResponse",
    "NewCampaign",
    "NewCharacter",
    "NewScene",
    "NewTurn",
    "SceneResponse",
    "ScoreResponse",
    "ScoresResponse",
    "SystemResponse",
    "TurnResponse",
    "WantScores",
    "WorldResponse",
]
