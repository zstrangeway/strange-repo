"""Known accounts for local development.

Idempotent: re-running resets these users to the passwords below rather
than failing on the unique email, so a half-broken local database is one
command away from usable again. It reports every account either way —
a seed step that silently does nothing is worse than no seed step.

Refuses to touch anything but a local database, because "put the schema
back how I like it" is not a thing to run against production by accident.
"""

import asyncio
import sys
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from gary_api.db import database_url, engine
from gary_api.models import User
from gary_api.passwords import hash_password

PASSWORD = "gary-local-password"

ACCOUNTS = [
    ("ada@example.com", "Ada Lovelace"),
    ("alan@example.com", "Alan Turing"),
    ("grace@example.com", "Grace Hopper"),
]

LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "db", "postgres"})


def is_local(url: str) -> bool:
    # The host is compared whole, not searched for: a substring test would
    # read localhost.someone-elses-domain.com as local and seed it.
    try:
        host = urlsplit(url).hostname
    except ValueError:
        return False

    return host in LOCAL_HOSTS


async def seed() -> list[str]:
    """Create or reset the development accounts. Returns a line per account."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    lines = []

    async with factory() as database:
        for email, display_name in ACCOUNTS:
            user = await database.scalar(select(User).where(User.email == email))
            if user is None:
                database.add(
                    User(
                        email=email,
                        display_name=display_name,
                        password_hash=hash_password(PASSWORD),
                    )
                )
                lines.append(f"  created  {email}  ({display_name})")
            else:
                user.display_name = display_name
                user.password_hash = hash_password(PASSWORD)
                database.add(user)
                lines.append(f"  reset    {email}  ({display_name})")

        await database.commit()

    return lines


def main() -> int:
    url = database_url()
    if not is_local(url):
        print(
            "seed: refusing to run — DATABASE_URL does not look local.\n"
            "      These accounts have a published password and would be a way in.",
            file=sys.stderr,
        )
        return 1

    lines = asyncio.run(seed())

    print("seed: development accounts")
    for line in lines:
        print(line)
    print(f"\n  password for all of them: {PASSWORD}\n")
    return 0
