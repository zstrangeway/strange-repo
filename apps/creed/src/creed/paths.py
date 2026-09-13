"""Where creed keeps things.

One directory holds the database and nothing else, so the whole local state
is a folder somebody can delete when they want a clean sync. ``CREED_HOME``
moves it; the default is under the user's cache directory rather than the
working directory, because unlike a job search this is a copy of somebody
else's public data and there is no reason to have one per project.
"""

import os
from pathlib import Path


def home() -> Path:
    """The directory creed works in."""
    configured = os.environ.get("CREED_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    cache = os.environ.get("XDG_CACHE_HOME") or "~/.cache"
    return (Path(cache).expanduser() / "creed").resolve()


def database_path() -> Path:
    """The SQLite file. Created on first use, along with its directory."""
    return home() / "creed.db"


def staging_path() -> Path:
    """Where a sync builds the next database before it replaces the live one.

    A sync writes here and moves the result into place, so a sync that dies
    halfway leaves the previous database untouched rather than half-rewritten.
    """
    return home() / "creed.db.staging"
