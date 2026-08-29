"""The SQLite file and its schema.

stdlib ``sqlite3``: no driver to install and nothing to compile, which is most
of why a fresh clone reaches a logged application in five minutes.

The schema is applied on every connect rather than by a migration tool. There
is one table set, it is small, and ``CREATE TABLE IF NOT EXISTS`` is honest
about what it does — a migration framework here would be machinery guarding a
file that lives on one laptop.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from . import paths

SCHEMA = """
CREATE TABLE IF NOT EXISTS postings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ref         TEXT    NOT NULL UNIQUE,
    title       TEXT,
    company     TEXT,
    source_url  TEXT    UNIQUE,
    body        TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);

-- Append-only. A status is never updated in place, because the question
-- people actually have months later is "when did I apply and how long did
-- they sit on it", and a mutable status column throws that away every time
-- it is written. The current status is the last row here with one set.
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    posting_id  INTEGER NOT NULL REFERENCES postings(id) ON DELETE CASCADE,
    status      TEXT,
    note        TEXT,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS resumes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    posting_id  INTEGER NOT NULL REFERENCES postings(id) ON DELETE CASCADE,
    version     INTEGER NOT NULL,
    path        TEXT    NOT NULL,
    summary     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    UNIQUE (posting_id, version)
);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """A connection with the schema applied and foreign keys on.

    Committed on a clean exit and rolled back on an exception, so a tailoring
    that fails its grounding check leaves nothing behind.
    """
    path = paths.database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    # Off by default in SQLite, and the cascade above is a lie without it.
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    try:
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
