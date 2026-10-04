"""Backward-compatible shim for the old monolithic play module.

`apps/gary-api/src/gary_api/play.py` was split into the `gary_api.play`
package. This file keeps old imports working until they are moved.
"""

from gary_api.play import (  # noqa: F401
    OPENING,
    NewTurn,
    _run,
    _sheet_for,
    begin_campaign,
    router,
    take_turn,
)
from gary_api.play.schemas import *  # noqa: F401,F403
