import asyncio
import io
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient

from gary_api import db, identity, logs
from gary_api.app import app
from gary_api.db import database_url
from gary_api.models import Base


def _engine():
    """A throwaway engine, pooling disabled.

    behave drives async work through a fresh event loop each time, and a
    pooled connection opened on one loop blows up when reused on the next.
    Nothing here is hot enough to want a pool.
    """
    return create_async_engine(database_url(), poolclass=NullPool)


def _run(work):
    async def scoped():
        engine = _engine()
        try:
            return await work(engine)
        finally:
            await engine.dispose()

    return asyncio.run(scoped())


def before_all(context):
    # The fake identity provider stands in for Google, Facebook and Apple.
    # Reaching the real three would need their consent screens driven by
    # hand, and what these specs are about is what gary does with an answer,
    # not whether Google can authenticate people.
    os.environ["IDENTITY_FAKE"] = "1"

    async def build(engine):
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

    _run(build)


def before_scenario(context, scenario):
    # A fresh engine per scenario, for the same loop reason, and because one
    # scenario deliberately points db.engine at a dead database.
    db.engine = _engine()

    # Cleared per scenario: provider() caches what it built, and a scenario
    # that changes which providers are configured would otherwise leak into
    # the next one.
    os.environ["IDENTITY_FAKE"] = "1"
    os.environ.pop("IDENTITY_PROVIDERS", None)
    identity.provider.cache_clear()

    async def empty(engine):
        async with engine.begin() as connection:
            # CASCADE reaches sessions and identities through their foreign
            # keys, so this cannot drift as tables are added.
            await connection.execute(text("TRUNCATE users CASCADE"))

    _run(empty)

    # The real configuration, pointed at a buffer instead of stdout. Reading
    # what the shipped formatter produced is the whole point — a spec that
    # asserted against a formatter built here would agree with itself.
    os.environ.pop("LOG_LEVEL", None)
    os.environ.pop("LOG_FORMAT", None)
    context.log = io.StringIO()
    logs.configure(stream=context.log)

    context.client = TestClient(app)
    context.response = None
    context.token = None
    context.other_token = None
    context.identities = {}
    context.accounts = {}


def after_scenario(context, scenario):
    context.client.close()
    identity.provider.cache_clear()


def sql(statement, **parameters):
    """Run a statement outside the app, for arranging and asserting."""

    async def run(engine):
        async with engine.begin() as connection:
            result = await connection.execute(text(statement), parameters)
            return result.fetchall() if result.returns_rows else []

    return _run(run)
