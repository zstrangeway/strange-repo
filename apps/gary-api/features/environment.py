import asyncio
import io
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient

from gary_api import db, logs, mail
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


class FakeResend:
    """A local stand-in for Resend's API, not for our own mail code.

    The specs run the real ResendMailer over real HTTP against this, so what
    they prove is what gary actually sends. Nothing here is registered into
    PROVIDERS — the provider under test is the shipped one, selected the way
    a deployment selects it.
    """

    def __init__(self):
        self.sent = []
        self.refusing = False
        self.server = HTTPServer(("127.0.0.1", 0), self._handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        host, port = self.server.server_address
        return f"http://{host}:{port}/emails"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def _handler(fake):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(
                    self.rfile.read(int(self.headers["content-length"]))
                )
                if fake.refusing:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(b"the fake provider is refusing everything")
                    return

                fake.sent.append(body)
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"id": "sent"}')

            def log_message(self, *args):
                pass

        return Handler


def before_all(context):
    # The real Resend provider, pointed at a local server. RESEND_API_URL is
    # what keeps a real key in the environment from reaching Resend, so it is
    # set before anything can resolve a mailer, and the key is overridden too.
    context.mail = FakeResend()
    os.environ["MAIL_PROVIDER"] = "resend"
    os.environ["RESEND_API_KEY"] = "not-a-real-key"
    os.environ["RESEND_API_URL"] = context.mail.url

    async def build(engine):
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

    _run(build)


def before_scenario(context, scenario):
    # A fresh engine per scenario, for the same loop reason, and because one
    # scenario deliberately points db.engine at a dead database.
    db.engine = _engine()

    context.mail.sent.clear()
    context.mail.refusing = False
    # Restored per scenario, not just once: one spec swaps in the console
    # provider, and the next one along would otherwise inherit it.
    os.environ["MAIL_PROVIDER"] = "resend"
    mail.mailer.cache_clear()

    async def empty(engine):
        async with engine.begin() as connection:
            # CASCADE reaches sessions and reset tokens through their
            # foreign keys, so this cannot drift as tables are added.
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
    context.first_token = None
    context.first_verification = None
    context.reset_token = None
    context.mail_baseline = 0


def before_step(context, step):
    # "no email should be sent" means none sent by the action under test, not
    # none in the whole scenario — arranging an account now mails too.
    if step.step_type == "when":
        context.mail_baseline = len(context.mail.sent)


def after_scenario(context, scenario):
    context.client.close()
    mail.mailer.cache_clear()


def after_all(context):
    context.mail.close()


def sql(statement, **parameters):
    """Run a statement outside the app, for arranging and asserting."""

    async def run(engine):
        async with engine.begin() as connection:
            result = await connection.execute(text(statement), parameters)
            return result.fetchall() if result.returns_rows else []

    return _run(run)
