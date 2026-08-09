import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient

from gary_api import db, mail
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


class MailSpy:
    """Stands in for a provider and keeps what it was handed.

    Registered as a provider rather than patched over mail.send, so the specs
    go through the same selection path a deployment does.
    """

    name = "spy"

    def __init__(self):
        self.sent = []
        self.refusing = False

    async def send(self, message):
        if self.refusing:
            raise mail.MailError("the spy is refusing everything")
        self.sent.append(message)


def before_all(context):
    # Belt and braces with the test task's MAIL_PROVIDER pin: a real key in
    # the environment must never turn a spec run into real email.
    os.environ["MAIL_PROVIDER"] = "spy"

    async def build(engine):
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

    _run(build)


def before_scenario(context, scenario):
    # A fresh engine per scenario, for the same loop reason, and because one
    # scenario deliberately points db.engine at a dead database.
    db.engine = _engine()

    context.mail = MailSpy()
    mail.PROVIDERS["spy"] = lambda: context.mail
    mail.mailer.cache_clear()

    async def empty(engine):
        async with engine.begin() as connection:
            # CASCADE reaches sessions and reset tokens through their
            # foreign keys, so this cannot drift as tables are added.
            await connection.execute(text("TRUNCATE users CASCADE"))

    _run(empty)

    context.client = TestClient(app)
    context.response = None
    context.token = None
    context.other_token = None
    context.first_token = None
    context.reset_token = None


def after_scenario(context, scenario):
    context.client.close()
    mail.mailer.cache_clear()
    mail.PROVIDERS.pop("spy", None)


def sql(statement, **parameters):
    """Run a statement outside the app, for arranging and asserting."""

    async def run(engine):
        async with engine.begin() as connection:
            result = await connection.execute(text(statement), parameters)
            return result.fetchall() if result.returns_rows else []

    return _run(run)
