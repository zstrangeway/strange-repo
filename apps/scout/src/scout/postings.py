"""Saving a posting, and reading it back.

A posting is the first thing in scout that belongs to somebody: a tailored
resume and an application's history both hang off one. Nothing here talks to a
model, which is why saving works with no API key at all.
"""

import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from . import applications, fetch
from .errors import ScoutError

UNKNOWN_COMPANY = "unknown"


@dataclass(frozen=True)
class Posting:
    id: int
    ref: str
    title: str | None
    company: str | None
    source_url: str | None
    body: str
    created_at: str

    @property
    def company_or_unknown(self) -> str:
        return self.company or UNKNOWN_COMPANY


def _slug(text: str) -> str:
    """A ref somebody can type, and a directory name that is safe anywhere."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60].strip("-")


def _unique_ref(connection: sqlite3.Connection, base: str) -> str:
    base = base or "posting"
    ref, n = base, 1
    while connection.execute("SELECT 1 FROM postings WHERE ref = ?", (ref,)).fetchone():
        n += 1
        ref = f"{base}-{n}"
    return ref


def _row_to_posting(row: sqlite3.Row) -> Posting:
    return Posting(
        id=row["id"],
        ref=row["ref"],
        title=row["title"],
        company=row["company"],
        source_url=row["source_url"],
        body=row["body"],
        created_at=row["created_at"],
    )


def save(
    connection: sqlite3.Connection,
    *,
    text: str | None = None,
    url: str | None = None,
    title: str | None = None,
    company: str | None = None,
) -> Posting:
    """Save a posting from pasted text or a URL.

    The company is never guessed. A wrong company is worse than a blank one:
    it is the field somebody reads back weeks later to remember who they wrote
    to, and a plausible guess is indistinguishable from a fact once it is in
    the row.
    """
    if url is not None:
        existing = connection.execute(
            "SELECT * FROM postings WHERE source_url = ?", (url,)
        ).fetchone()
        if existing is not None:
            raise ScoutError(
                f"That URL is already saved as {existing['ref']}.",
                detail=(
                    "Applying twice to the same posting is nearly always an "
                    f"accident. Read it with: scout show {existing['ref']}"
                ),
            )
        text, found_title = fetch.posting_from_url(url)
        title = title or found_title

    body = (text or "").strip()
    if not body:
        raise ScoutError(
            "That posting was empty.",
            detail="Nothing was saved. Pass --text with the posting in it, "
            "or --url to fetch one.",
        )

    ref = _unique_ref(connection, _slug(" ".join(filter(None, [company, title]))))
    now = datetime.now(UTC).isoformat(timespec="seconds")
    cursor = connection.execute(
        "INSERT INTO postings (ref, title, company, source_url, body, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (ref, title, company, url, body, now),
    )
    posting_id = cursor.lastrowid
    # In the same transaction as the posting: a posting whose log does not say
    # it was saved would have no status at all.
    applications.record(connection, posting_id, "saved")
    return read(connection, ref)


def read(connection: sqlite3.Connection, ref: str) -> Posting:
    row = connection.execute("SELECT * FROM postings WHERE ref = ?", (ref,)).fetchone()
    if row is None:
        raise ScoutError(
            f"There is no posting called {ref}.",
            detail="Run `scout list` to see what there is.",
        )
    return _row_to_posting(row)


def all_postings(
    connection: sqlite3.Connection, *, in_play_only: bool = False
) -> list[Posting]:
    """Every posting, newest first.

    ``in_play_only`` drops the ones that ended — which is the list somebody
    wants on a Monday morning.
    """
    rows = connection.execute("SELECT * FROM postings ORDER BY id DESC").fetchall()
    postings = [_row_to_posting(row) for row in rows]
    if in_play_only:
        postings = [
            posting
            for posting in postings
            if applications.current_status(connection, posting.id)
            not in applications.ENDINGS
        ]
    return postings


def edit(
    connection: sqlite3.Connection,
    ref: str,
    *,
    title: str | None = None,
    company: str | None = None,
) -> Posting:
    """Fill in what scout would not guess."""
    posting = read(connection, ref)
    if title is None and company is None:
        raise ScoutError("Nothing to change. Pass --title or --company.")
    connection.execute(
        "UPDATE postings SET title = ?, company = ? WHERE id = ?",
        (title or posting.title, company or posting.company, posting.id),
    )
    return read(connection, ref)
