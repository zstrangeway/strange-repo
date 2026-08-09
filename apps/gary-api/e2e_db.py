"""Throwaway databases for end-to-end runs.

Creates a uniquely named database on whatever server DATABASE_URL points at,
empties it between scenarios, and drops it at the end. Ephemeral means the
database, not the server — so this works against a developer's local Postgres
and against a CI service container without either needing Docker.

Test infrastructure, deliberately outside src/ so it is not part of what the
coverage gate measures.

    python e2e_db.py create gary_e2e_ab12cd34   # prints the URL to use
    python e2e_db.py reset  gary_e2e_ab12cd34
    python e2e_db.py drop   gary_e2e_ab12cd34
"""

import asyncio
import re
import sys
from urllib.parse import urlsplit, urlunsplit

import asyncpg

from gary_api.db import database_url

# Interpolated into SQL, which cannot take a parameter for an identifier, so
# the shape is pinned rather than trusted.
NAME = re.compile(r"^gary_e2e_[a-z0-9_]{4,40}$")

# Somewhere to be connected while creating or dropping another database.
MAINTENANCE = "postgres"


def dsn(database: str) -> str:
    parts = urlsplit(database_url().replace("+asyncpg", ""))
    return urlunsplit((parts.scheme, parts.netloc, f"/{database}", "", ""))


async def _run(database: str, *statements: str) -> None:
    connection = await asyncpg.connect(dsn(database))
    try:
        for statement in statements:
            await connection.execute(statement)
    finally:
        await connection.close()


async def create(name: str) -> None:
    # DROP first so a crashed run does not block the next one.
    await _run(MAINTENANCE, f'DROP DATABASE IF EXISTS "{name}"', f'CREATE DATABASE "{name}"')


async def drop(name: str) -> None:
    await _run(MAINTENANCE, f'DROP DATABASE IF EXISTS "{name}"')


async def reset(name: str) -> None:
    # CASCADE reaches sessions and reset tokens through their foreign keys.
    await _run(name, "TRUNCATE users CASCADE")


def main(argv: list[str]) -> int:
    actions = {"create": create, "drop": drop, "reset": reset}

    if len(argv) != 3 or argv[1] not in actions:
        print(f"usage: e2e_db.py {'|'.join(actions)} <name>", file=sys.stderr)
        return 2

    action, name = argv[1], argv[2]
    if not NAME.match(name):
        print(f"e2e_db: refusing {name!r}; must match {NAME.pattern}", file=sys.stderr)
        return 2

    asyncio.run(actions[action](name))

    if action == "create":
        print(dsn(name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
