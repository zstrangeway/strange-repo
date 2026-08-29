"""Where an application got to.

The status is a fold over an append-only log rather than a column. Same choice
gary makes with levels: what gets shown is a fact derived from what happened,
not a value somebody remembered to keep up to date.
"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from .errors import ScoutError

# The path forward, in order. Index in this list is what makes a transition
# legal or not.
PATH = ("saved", "applied", "screening", "interview", "offer")

# Reachable from anywhere on the path, at any point.
ENDINGS = ("rejected", "ghosted")

STATUSES = PATH + ENDINGS


def allowed_from(status: str) -> tuple[str, ...]:
    """The statuses that may follow ``status``.

    Forward one step along the path, or out to an ending. The path is enforced
    because the mistake it catches is real: logging "offer" against the wrong
    posting out of a list of thirty. Refusing it at the moment it happens is
    what makes the slip visible, rather than a status report weeks later.
    """
    if status in ENDINGS:
        # Not a grave. Recruiters resurface, and when one does the log should
        # be able to say so rather than making somebody start the posting
        # again. Everything but `saved`, which cannot be returned to — the
        # posting is saved already.
        return PATH[1:]
    following = PATH.index(status) + 1
    return PATH[following : following + 1] + ENDINGS


@dataclass(frozen=True)
class Event:
    """One line of the log. A note with no status is still an entry."""

    status: str | None
    note: str | None
    at: str


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def record(
    connection: sqlite3.Connection,
    posting_id: int,
    status: str | None,
    note: str | None = None,
) -> None:
    """Append to the log. Nothing here ever updates a row."""
    connection.execute(
        "INSERT INTO events (posting_id, status, note, created_at) VALUES (?, ?, ?, ?)",
        (posting_id, status, note, _now()),
    )


def history(connection: sqlite3.Connection, posting_id: int) -> list[Event]:
    rows = connection.execute(
        "SELECT status, note, created_at FROM events WHERE posting_id = ? ORDER BY id",
        (posting_id,),
    ).fetchall()
    return [Event(r["status"], r["note"], r["created_at"]) for r in rows]


def current_status(connection: sqlite3.Connection, posting_id: int) -> str:
    """The last status logged.

    Never None in practice: saving a posting writes its `saved` entry in the
    same transaction that writes the posting, so a posting without one does
    not exist.
    """
    row = connection.execute(
        "SELECT status FROM events WHERE posting_id = ? AND status IS NOT NULL"
        " ORDER BY id DESC LIMIT 1",
        (posting_id,),
    ).fetchone()
    return row["status"]


def last_moved(connection: sqlite3.Connection, posting_id: int) -> str:
    row = connection.execute(
        "SELECT created_at FROM events WHERE posting_id = ? AND status IS NOT NULL"
        " ORDER BY id DESC LIMIT 1",
        (posting_id,),
    ).fetchone()
    return row["created_at"]


def check_transition(current: str, wanted: str) -> None:
    """Raise unless ``wanted`` may follow ``current``."""
    if wanted not in STATUSES:
        raise ScoutError(
            f'"{wanted}" is not a status scout knows.',
            detail="The statuses are: " + ", ".join(STATUSES) + ".",
        )
    allowed = allowed_from(current)
    if wanted not in allowed:
        raise ScoutError(
            f'This posting is at "{current}", so it cannot go to "{wanted}".',
            detail=f'From "{current}" you can log: ' + ", ".join(allowed) + ".",
        )
