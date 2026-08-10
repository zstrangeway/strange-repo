"""Known accounts for local development.

Each is reachable by signing in through the fake identity provider, which
is what IDENTITY_FAKE=1 turns on. The sign-in code for an account is
printed below; there are no passwords to seed any more.

Idempotent: re-running leaves existing accounts as they are rather than
failing, so a half-broken local database is one command away from usable
again. It reports every account either way — a seed step that silently
does nothing is worse than no seed step.

Refuses to touch anything but a local database, because "put the schema
back how I like it" is not a thing to run against production by accident.
"""

import asyncio
import sys
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from gary_api.db import database_url, engine
from gary_api.models import Identity, User

# The provider seeded accounts are reachable through. Any of the three would
# do — the fake stands in for all of them — and google is the one a local
# sign-in page lists first.
PROVIDER = "google"

ACCOUNTS = [
    ("ada@example.com", "Ada Lovelace"),
    ("alan@example.com", "Alan Turing"),
    ("grace@example.com", "Grace Hopper"),
]


def sign_in_code(email: str, display_name: str) -> str:
    """What to paste into the fake provider to become this account."""
    return f"seed-{email}|{email}|{display_name}"

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
            subject = f"seed-{email}"
            # Looked up by identity rather than address, the same way signing
            # in does, so seeding cannot create a second account for someone
            # who already has one under a different address.
            found = await database.scalar(
                select(Identity).where(
                    Identity.provider == PROVIDER, Identity.subject == subject
                )
            )
            if found is None:
                user = User(email=email, display_name=display_name)
                database.add(user)
                await database.flush()
                database.add(
                    Identity(
                        user_id=user.id,
                        provider=PROVIDER,
                        subject=subject,
                        email=email,
                    )
                )
                lines.append(f"  created  {email}  ({display_name})")
            else:
                lines.append(f"  present  {email}  ({display_name})")

        await database.commit()

    return lines


def main() -> int:
    url = database_url()
    if not is_local(url):
        print(
            "seed: refusing to run — DATABASE_URL does not look local.\n"
            "      These accounts are reachable with a published sign-in code\n"
            "      and would be a way in.",
            file=sys.stderr,
        )
        return 1

    lines = asyncio.run(seed())

    print("seed: development accounts")
    for line in lines:
        print(line)

    print("\n  sign in with IDENTITY_FAKE=1 and one of these codes:\n")
    for email, display_name in ACCOUNTS:
        print(f"    {sign_in_code(email, display_name)}")
    print()
    return 0
