"""The SQLite file and its schema.

stdlib ``sqlite3``: nothing to install, nothing to compile, and the export is
a read-only 8.4MB of relational tables joined on string ids — which is a
query, not a dictionary lookup. FTS5 comes in the same box and does the name
searching.

Two kinds of table live here, and the difference decides everything about
syncing. The export tables are a copy of somebody else's data and a sync
replaces them wholesale. The army list tables are the user's own and a sync
must never touch them, which is why the staging database a sync builds is
copied *from* the live one for those tables before it replaces it.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from . import export, paths

# Tables holding the user's own work. Named here because sync.py needs to know
# exactly which rows to carry across when it swaps the database, and a list
# that goes missing on a Tuesday because somebody added a table and forgot is
# the kind of bug that loses trust permanently.
USER_TABLES = ("lists", "list_units", "list_unit_wargear")

USER_SCHEMA = """
CREATE TABLE IF NOT EXISTS lists (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL UNIQUE,
    faction_id    TEXT    NOT NULL,
    points_limit  INTEGER NOT NULL,
    detachment_id TEXT,
    created_at    TEXT    NOT NULL
);

-- One unit in a list. `position` is what decides the price: 11th edition
-- charges by how many of a datasheet the army already holds, so the third
-- Custodian Guard can cost more than the first, and the order units were
-- added in is the only thing that says which is the third.
CREATE TABLE IF NOT EXISTS list_units (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id        INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
    datasheet_id   TEXT    NOT NULL,
    models         INTEGER NOT NULL,
    position       INTEGER NOT NULL,
    enhancement_id TEXT,
    attached_to    INTEGER REFERENCES list_units(id) ON DELETE SET NULL,
    created_at     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS list_unit_wargear (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    list_unit_id INTEGER NOT NULL REFERENCES list_units(id) ON DELETE CASCADE,
    description  TEXT    NOT NULL,
    quantity     INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS list_units_by_list ON list_units(list_id, position);
"""

# What creed knows about the sync itself: which export version is loaded, when
# it last looked, and the per-file validators that make conditional GET work.
META_SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_state (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS sync_validators (
    table_name    TEXT PRIMARY KEY,
    etag          TEXT,
    last_modified TEXT
);
"""


def export_schema() -> str:
    """DDL for the export tables, generated from the specification.

    Generated rather than written out, so a table added to export.py cannot be
    one somebody forgot to create here. Every column is TEXT because every
    column in the export is text — costs included, since a cost cell is empty
    on the section-header rows.
    """
    statements = []
    for table in export.TABLES:
        columns = ",\n    ".join(f'"{name}" TEXT' for name in table.columns)
        statements.append(
            f'CREATE TABLE IF NOT EXISTS "{table.name}" (\n    {columns}\n);'
        )
        for index in table.indexes:
            cols = ", ".join(f'"{c}"' for c in index)
            suffix = "_".join(index)
            statements.append(
                f'CREATE INDEX IF NOT EXISTS "{table.name}_by_{suffix}" '
                f'ON "{table.name}" ({cols});'
            )
    # Name search wants to survive a typo and a partial word, and FTS5 is in
    # the same stdlib module as everything else here.
    statements.append(
        "CREATE VIRTUAL TABLE IF NOT EXISTS datasheet_search "
        'USING fts5(datasheet_id UNINDEXED, name, tokenize="unicode61");'
    )
    return "\n\n".join(statements)


def apply_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(export_schema())
    connection.executescript(META_SCHEMA)
    connection.executescript(USER_SCHEMA)


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Open the database, creating it and its directory if need be."""
    target = path or paths.database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    apply_schema(connection)
    return connection


@contextmanager
def session(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    connection = connect(path)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def get_state(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute(
        "SELECT value FROM sync_state WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row else None


def set_state(connection: sqlite3.Connection, key: str, value: str | None) -> None:
    connection.execute(
        "INSERT INTO sync_state (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
