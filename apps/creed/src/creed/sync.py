"""Pulling the export in, without ever showing a half-pulled one.

Two properties matter more than speed here.

The first is that a sync is all or nothing. Eight megabytes over twenty-one
requests has room to fail halfway, and a database holding new stratagems
joined to old datasheets is worse than one holding yesterday's everything,
because nothing about it looks wrong. So a sync works on a copy and moves it
into place at the end: a failure leaves the previous database exactly as it
was.

The second is that the copy starts as the live database rather than as an
empty one. That is what lets conditional GET actually save anything — a table
that answers 304 keeps the rows already there — and it is what carries the
user's army lists across a sync that replaces every export table around them.
"""

import os
import re
import shutil
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from . import db, export, paths
from .fetch import ExportUnreachableError, Fetcher, Validators

# The export is pipe-delimited, UTF-8 with a BOM. The BOM lands on the first
# header name, so reading it as plain utf-8 leaves the first column called
# "﻿id" and every lookup against it silently misses.
DELIMITER = "|"
ENCODING = "utf-8-sig"

# A record ends with the delimiter and then a newline. See _records for why
# this rather than the csv module.
RECORD_SEPARATOR = re.compile(re.escape("|") + r"\r?\n")

LAST_UPDATE_KEY = "export_last_update"
LAST_CHECKED_KEY = "last_checked_at"


class MalformedTableError(Exception):
    """A table came back in a shape creed does not recognise.

    Deliberately not an ExportUnreachable: this one means the export changed
    and creed needs changing to match, which is a different message and a
    different response from "try again when the wifi is back".
    """


@dataclass
class TableResult:
    name: str
    rows: int = 0
    downloaded: bool = False


@dataclass
class SyncResult:
    """What a sync did, in enough detail to print or to assert on."""

    tables: list[TableResult] = field(default_factory=list)
    last_update: str | None = None
    already_current: bool = False
    failed: str | None = None

    @property
    def rows(self) -> int:
        return sum(t.rows for t in self.tables)

    @property
    def downloaded(self) -> list[str]:
        return [t.name for t in self.tables if t.downloaded]

    @property
    def not_modified(self) -> list[str]:
        return [t.name for t in self.tables if not t.downloaded]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _records(text: str) -> list[list[str]]:
    """Split the export's own dialect into records, without the csv module.

    This looks like a CSV and cannot be read as one. Two things defeat
    ``csv.reader``:

    Rules text is full of double quotes, because ranges are written 6" and 24".
    The reader treats the first as opening a quoted field and swallows
    everything to the next one, merging rows that have nothing to do with each
    other. ``QUOTE_NONE`` fixes that and leaves the second problem.

    Descriptions contain literal newlines. A record is therefore not a line —
    in Stratagems.csv eight physical lines are continuations, and reading
    line-by-line yields rows with six fields where eleven were expected.

    What does hold: every record ends with the delimiter, and no field can
    contain one (it is the delimiter, and the export does not escape). So the
    record separator is a delimiter immediately followed by a newline, and
    splitting on that gives exactly the right field count for every table in
    the export — verified across all twenty.
    """
    return [
        record.split(export.DELIMITER)
        for record in re.split(RECORD_SEPARATOR, text)
        if record.strip()
    ]


def _parse(table: export.Table, text: str) -> list[tuple[str, ...]]:
    """Read one table, refusing anything whose columns have moved.

    The check is the point. A column added upstream is harmless and a column
    renamed or removed silently breaks whichever feature reads it, so the
    shape is verified once here rather than discovered later as an answer that
    came back empty.
    """
    records = _records(text)
    if not records:
        raise MalformedTableError(f"{table.name}: the file was empty")
    header = [name.strip() for name in records[0]]
    missing = [name for name in table.columns if name not in header]
    if missing:
        raise MalformedTableError(
            f"{table.name}: expected columns {', '.join(missing)} "
            f"but the export sent {', '.join(header)}"
        )
    index = {name: position for position, name in enumerate(header)}
    width = len(header)
    rows = []
    for line, record in enumerate(records[1:], start=2):
        if len(record) != width:
            raise MalformedTableError(
                f"{table.name}: record {line} has {len(record)} fields, "
                f"expected {width}"
            )
        rows.append(tuple(record[index[name]] for name in table.columns))
    return rows


def _load(connection: sqlite3.Connection, table: export.Table, rows) -> None:
    columns = ", ".join(f'"{name}"' for name in table.columns)
    placeholders = ", ".join("?" for _ in table.columns)
    connection.execute(f'DELETE FROM "{table.name}"')
    connection.executemany(
        f'INSERT INTO "{table.name}" ({columns}) VALUES ({placeholders})', rows
    )


def _rebuild_search_index(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM datasheet_search")
    connection.execute(
        "INSERT INTO datasheet_search (datasheet_id, name) "
        'SELECT "id", "name" FROM "Datasheets"'
    )


def _validators(connection: sqlite3.Connection, name: str) -> Validators:
    row = connection.execute(
        "SELECT etag, last_modified FROM sync_validators WHERE table_name = ?",
        (name,),
    ).fetchone()
    if row is None:
        return Validators()
    return Validators(etag=row["etag"], last_modified=row["last_modified"])


def _remember_validators(
    connection: sqlite3.Connection, name: str, etag: str | None, modified: str | None
) -> None:
    connection.execute(
        "INSERT INTO sync_validators (table_name, etag, last_modified) "
        "VALUES (?, ?, ?) ON CONFLICT(table_name) DO UPDATE SET "
        "etag = excluded.etag, last_modified = excluded.last_modified",
        (name, etag, modified),
    )


def read_marker(fetcher: Fetcher) -> str:
    """The export's own timestamp: one 39-byte request covering everything."""
    table = export.marker_table()
    response = fetcher.get(table, Validators())
    rows = _parse(table, response.text)
    if not rows:
        raise MalformedTableError(f"{table.name}: no timestamp in the file")
    return rows[0][0].strip()


def status() -> dict[str, object]:
    """What creed holds and how old it is, without going near the network."""
    with db.session() as connection:
        last_update = db.get_state(connection, LAST_UPDATE_KEY)
        counts = {}
        if last_update:
            for table in export.data_tables():
                counts[table.name] = connection.execute(
                    f'SELECT COUNT(*) AS n FROM "{table.name}"'
                ).fetchone()["n"]
        return {
            "last_update": last_update,
            "last_checked": db.get_state(connection, LAST_CHECKED_KEY),
            "synced": last_update is not None,
            "rows": sum(counts.values()),
            "tables": counts,
        }


def check(fetcher: Fetcher | None = None) -> dict[str, object]:
    """Ask whether anything moved, paying for one small file to find out."""
    with Fetcher() if fetcher is None else _Borrowed(fetcher) as client:
        marker = read_marker(client)
    with db.session() as connection:
        held = db.get_state(connection, LAST_UPDATE_KEY)
        db.set_state(connection, LAST_CHECKED_KEY, _now())
    return {"export": marker, "held": held, "stale": held != marker}


class _Borrowed:
    """Use a fetcher somebody else opened, without closing it for them."""

    def __init__(self, fetcher: Fetcher) -> None:
        self._fetcher = fetcher

    def __enter__(self) -> Fetcher:
        return self._fetcher

    def __exit__(self, *exc_info: object) -> None:
        return None


def sync(
    fetcher: Fetcher | None = None,
    force: bool = False,
    on_progress: Callable[[str], None] | None = None,
) -> SyncResult:
    """Bring the local database up to the export, or leave it exactly as it is.

    ``on_progress`` is where the running commentary goes. It is a callback
    rather than a print because stdout belongs to the MCP protocol, and one
    stray line there is a server that will not connect with nothing to read.
    """
    report = on_progress or (lambda message: None)
    result = SyncResult()
    staging = paths.staging_path()
    live = paths.database_path()

    with Fetcher() if fetcher is None else _Borrowed(fetcher) as client:
        marker = read_marker(client)
        result.last_update = marker

        with db.session() as connection:
            held = db.get_state(connection, LAST_UPDATE_KEY)
            db.set_state(connection, LAST_CHECKED_KEY, _now())
        if held == marker and not force:
            result.already_current = True
            # Deliberately not reported here. Both callers say this in their
            # own words, and saying it here too printed it twice.
            return result

        # Start from what is already here: unchanged tables keep their rows
        # without being downloaded, and the army lists come across untouched.
        staging.parent.mkdir(parents=True, exist_ok=True)
        staging.unlink(missing_ok=True)
        if live.exists():
            shutil.copyfile(live, staging)

        try:
            connection = db.connect(staging)
            try:
                for table in export.data_tables():
                    response = client.get(table, _validators(connection, table.name))
                    entry = TableResult(name=table.name)
                    if response.changed:
                        rows = _parse(table, response.text)
                        _load(connection, table, rows)
                        entry.rows = len(rows)
                        entry.downloaded = True
                        report(f"{table.name}: {len(rows)} rows")
                    else:
                        entry.rows = connection.execute(
                            f'SELECT COUNT(*) AS n FROM "{table.name}"'
                        ).fetchone()["n"]
                        report(f"{table.name}: unchanged")
                    _remember_validators(
                        connection, table.name, response.etag, response.last_modified
                    )
                    result.tables.append(entry)
                _rebuild_search_index(connection)
                db.set_state(connection, LAST_UPDATE_KEY, marker)
                db.set_state(connection, LAST_CHECKED_KEY, _now())
                connection.commit()
            finally:
                connection.close()
        except (ExportUnreachableError, MalformedTableError, sqlite3.Error) as error:
            staging.unlink(missing_ok=True)
            result.failed = str(error)
            report(f"sync failed: {error}")
            return result

    # The swap. os.replace is atomic on every platform creed runs on, so a
    # reader either sees the whole old database or the whole new one.
    os.replace(staging, live)
    # No summary line here. `on_progress` reports per-table detail; the
    # caller says what the whole sync amounted to, in its own words, and
    # doing both printed every outcome twice.
    return result
