"""Backward-compatible shim for ``gary_api.play``.

``play.py`` has been split into the ``gary_api.play`` package.  This
module re-exports the public surface so existing imports keep working.
"""

from gary_api.play import *  # noqa: F401,F403
from gary_api.play import router
