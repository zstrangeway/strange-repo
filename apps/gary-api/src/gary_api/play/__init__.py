"""Backward-compatible re-exports for the split play package."""

from gary_api.play.campaigns import _sheet_for
from gary_api.play.engine import OPENING, _run
from gary_api.play.router import begin_campaign, router, take_turn
from gary_api.play.schemas import NewTurn

__all__ = [
    "router",
    "take_turn",
    "begin_campaign",
    "_run",
    "_sheet_for",
    "OPENING",
    "NewTurn",
]
