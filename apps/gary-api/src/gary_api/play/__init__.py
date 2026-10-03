"""Backward-compatible public surface for ``gary_api.play``.

Importing the route modules registers their handlers on ``router``.  The
names below are the ones callers and tests already reached for.
"""

from gary_api.play import catalogue, campaigns, engine, world_read
from gary_api.play.router import router

# Backward-compatible names used by callers and tests.
from gary_api.play.campaigns import _sheet_for
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

__all__ = [
    "router",
    "OPENING",
    "take_turn",
    "begin_campaign",
    "_run",
    "_sheet_for",
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
