import asyncio
import io
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient

from sqlalchemy.ext.asyncio import async_sessionmaker

from gary_api import db, dice, identity, logs, narration
from gary_api.narration import fake as fake_narrator
from gary_api.app import app, create_app
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

    # Rolled from a known place, so a spec can assert a number rather than
    # merely that a number arrived. Cleared and reapplied per scenario because
    # the generator is module state: without this a scenario would roll from
    # wherever the previous one left it.
    os.environ["DICE_SEED"] = "1234"
    dice.configure()

    # The stand-in for the model, for the same reason as the identity double:
    # what these specs are about is what gary does with a narration, not
    # whether a model can write one. Cleared per scenario because narrator()
    # caches what it built.
    os.environ["GM_FAKE"] = "1"
    os.environ.pop("GM_MODEL", None)
    os.environ.pop("SCENE_MODEL", None)
    narration.narrator.cache_clear()

    # What the double will do when a scene closes. Module state, because no
    # player message is being answered at a close — so unlike every other
    # directive it has to be arranged rather than read, and unlike every other
    # directive it can leak. Cleared here so it cannot.
    fake_narrator.ON_CLOSE = None
    fake_narrator.LAST_CLOSE = None

    # The scene bound, back to its default per scenario. A spec that wants a
    # four-turn scene sets it and must not hand that to the next one.
    os.environ.pop("SCENE_TURNS", None)
    os.environ.pop("SCENE_CHARS", None)

    # No key, so the model menu is the built-in list rather than whatever
    # OpenRouter is serving today. That is what makes these specs assert
    # against something that cannot change under them — and it exercises the
    # fallback, which is the path a keyless deployment actually takes.
    os.environ.pop("OPENROUTER_API_KEY", None)
    narration.models.forget()

    async def empty(engine):
        async with engine.begin() as connection:
            # CASCADE reaches sessions and identities through their foreign
            # keys — and now campaigns, and everything hanging off those — so
            # this cannot drift as tables are added.
            await connection.execute(text("TRUNCATE users CASCADE"))

    _run(empty)

    # The real configuration, pointed at a buffer instead of stdout. Reading
    # what the shipped formatter produced is the whole point — a spec that
    # asserted against a formatter built here would agree with itself.
    os.environ.pop("LOG_LEVEL", None)
    os.environ.pop("LOG_FORMAT", None)
    context.log = io.StringIO()
    logs.configure(stream=context.log)

    # Cleared for the same reason as the providers: the origins a browser
    # may call from are fixed when the app is built.
    os.environ.pop("BROWSER_ORIGINS", None)

    context.client = TestClient(app)

    def rebuild_app():
        """Stand up a second app, for a scenario that changed its settings."""
        context.client.close()
        context.client = TestClient(create_app())

    context.rebuild_app = rebuild_app
    context.response = None
    context.token = None
    context.other_token = None
    context.identities = {}
    context.accounts = {}


def after_scenario(context, scenario):
    context.client.close()
    identity.provider.cache_clear()
    narration.narrator.cache_clear()
    narration.models.forget()


def sql(statement, **parameters):
    """Run a statement outside the app, for arranging and asserting."""

    async def run(engine):
        async with engine.begin() as connection:
            result = await connection.execute(text(statement), parameters)
            return result.fetchall() if result.returns_rows else []

    return _run(run)


def with_session(work):
    """Run async work against a real session, outside the app.

    For steps that arrange world state. They call the same ``world.record``
    the model's tools will call, rather than writing rows behind its back — so
    what a scenario arranges has been through the same validation as anything
    that happens during play.
    """

    async def run(engine):
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            result = await work(session)
            await session.commit()
            return result

    return _run(run)
