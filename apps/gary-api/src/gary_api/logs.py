"""Structured logging.

One JSON object per line, so a log search can filter on fields rather than
grep for substrings. Call it like this::

    from gary_api import logs

    logger = logs.get_logger(__name__)
    logger.info("mail.sent", provider="resend", to=user.email)

which lands as::

    {"timestamp": "2026-08-09T17:50:00.123Z", "level": "info",
     "logger": "gary_api.mail", "message": "mail.sent", "app": "gary-api",
     "request_id": "5f2c...", "provider": "resend", "to": "ada@example.com"}

This configures the *root* logger rather than wrapping one of our own, so
records from uvicorn, SQLAlchemy and anything else using the standard
library come out in the same shape. A log where our lines are structured and
the framework's are not is still a log you have to grep.

    LOG_LEVEL   the floor. INFO by default.
    LOG_FORMAT  json (default) or text. text is for reading by eye — the
                console mail provider logs a whole reset email, and JSON
                escapes turn that into one long unreadable line.
"""

import json
import logging
import os
import sys
import time
import traceback
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

APP = "gary-api"

REQUEST_ID_HEADER = "x-request-id"

# The formatter owns these. A caller passing one gets it renamed with a
# trailing underscore rather than overwriting it — otherwise a stray
# level="urgent" quietly rewrites the field the log search filters on and
# the line ends up lying about itself.
RESERVED = frozenset({"timestamp", "level", "logger", "message", "app", "error"})

# Everything the standard library already puts on a record. What is left over
# is what a caller added, either through this module or through a plain
# ``extra=`` on a stdlib logger.
_STANDARD = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message",
    "asctime",
    "taskName",
}

# What a field cannot be called without either overwriting one of ours or
# being rejected by ``makeRecord``. These get a trailing underscore instead.
_UNSAFE = RESERVED | _STANDARD

_context: ContextVar[dict[str, Any]] = ContextVar("gary_log_context", default={})


def _timestamp(created: float) -> str:
    """ISO-8601, UTC, milliseconds. Sortable as text, which is the point."""
    moment = datetime.fromtimestamp(created, timezone.utc)
    return f"{moment:%Y-%m-%dT%H:%M:%S}.{moment.microsecond // 1000:03d}Z"


def _render(value: Any) -> str:
    """The last resort for a value json cannot represent.

    A log call is not worth an outage: losing the line, or worse raising
    inside the handler, is a bad trade for a field that did not serialise.
    """
    return repr(value)


def _merge(payload: dict[str, Any], fields: dict[str, Any]) -> None:
    for key, value in fields.items():
        payload[f"{key}_" if key in RESERVED else key] = value


def _error(exc_info: Any) -> dict[str, str]:
    kind, value, _ = exc_info
    return {
        "type": kind.__name__,
        "message": str(value),
        "stack": "".join(traceback.format_exception(*exc_info)).rstrip(),
    }


def payload(record: logging.LogRecord) -> dict[str, Any]:
    """The record as a flat dictionary, before it is rendered."""
    built: dict[str, Any] = {
        "timestamp": _timestamp(record.created),
        "level": record.levelname.lower(),
        "logger": record.name,
        "message": record.getMessage(),
        "app": APP,
    }

    _merge(built, _context.get())
    _merge(built, {k: v for k, v in vars(record).items() if k not in _STANDARD})

    if record.exc_info:
        built["error"] = _error(record.exc_info)

    return built


class JsonFormatter(logging.Formatter):
    """One object per line.

    Deliberately does not call the base implementation: that appends the
    traceback as trailing text, which would put a stack outside the object
    it belongs to and break the one-line-one-record rule every log shipper
    depends on. The stack goes in ``error.stack`` instead.
    """

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(payload(record), default=_render)


class TextFormatter(logging.Formatter):
    """The same fields, laid out for a person reading a terminal."""

    def format(self, record: logging.LogRecord) -> str:
        built = payload(record)
        error = built.pop("error", None)
        head = "{} {:<7} {} {}".format(
            built.pop("timestamp"),
            built.pop("level"),
            built.pop("logger"),
            built.pop("message"),
        )
        built.pop("app")

        rest = " ".join(f"{key}={value!r}" for key, value in built.items())
        line = f"{head}  {rest}" if rest else head
        return f"{line}\n{error['stack']}" if error else line


def _safe(fields: dict[str, Any]) -> dict[str, Any]:
    """Rename anything that would collide on its way into a record.

    ``makeRecord`` raises outright on a field that shadows one of its own
    attributes — ``name``, ``module``, ``message`` and a dozen more. A log
    call is not worth an exception, so those get the same trailing
    underscore the formatter gives its own fields.
    """
    return {f"{key}_" if key in _UNSAFE else key: value for key, value in fields.items()}


class Logger:
    """A standard logger that takes fields as keyword arguments.

    ``logger.info("mail.sent", provider="resend")`` rather than
    ``logger.info("mail.sent", extra={"provider": "resend"})``. Thin on
    purpose — underneath is an ordinary stdlib logger, so levels, handlers
    and third-party configuration all still apply.

    Not a ``LoggerAdapter``: that one's own signature is ``log(level, msg)``,
    so a field called ``level`` or ``msg`` is a TypeError before it reaches
    anything that could rename it.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def _emit(self, level: int, message: str, fields: dict[str, Any], failed: bool = False) -> None:
        self.logger.log(level, message, extra=_safe(fields), exc_info=failed)

    def debug(self, message: str, **fields: Any) -> None:
        self._emit(logging.DEBUG, message, fields)

    def info(self, message: str, **fields: Any) -> None:
        self._emit(logging.INFO, message, fields)

    def warning(self, message: str, **fields: Any) -> None:
        self._emit(logging.WARNING, message, fields)

    def error(self, message: str, **fields: Any) -> None:
        self._emit(logging.ERROR, message, fields)

    def critical(self, message: str, **fields: Any) -> None:
        self._emit(logging.CRITICAL, message, fields)

    def exception(self, message: str, **fields: Any) -> None:
        """An error, with the exception being handled attached to it."""
        self._emit(logging.ERROR, message, fields, failed=True)


def get_logger(name: str) -> Logger:
    return Logger(logging.getLogger(name))


@contextmanager
def bind(**fields: Any) -> Iterator[None]:
    """Add fields to every line logged inside the block, from anywhere.

    Including lines logged by code that knows nothing about this module,
    which is how a request id reaches SQLAlchemy's own records.
    """
    token = _context.set({**_context.get(), **fields})
    try:
        yield
    finally:
        _context.reset(token)


def context() -> dict[str, Any]:
    """The fields currently bound. Empty outside a bound block."""
    return dict(_context.get())


def configure(stream: Any = None) -> logging.Handler:
    """Install the formatter on the root logger. Safe to call twice."""
    text = os.environ.get("LOG_FORMAT", "json").lower() == "text"
    handler = logging.StreamHandler(sys.stdout if stream is None else stream)
    handler.setFormatter(TextFormatter() if text else JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

    # uvicorn installs handlers on its own loggers and stops them
    # propagating, so without this its access log stays plain text while
    # everything around it is JSON.
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        theirs = logging.getLogger(name)
        theirs.handlers = []
        theirs.propagate = True

    return handler


logger = get_logger(__name__)


class RequestContext:
    """Gives every request an id, and every line logged during it that id.

    Pure ASGI rather than a Starlette ``BaseHTTPMiddleware``: that one runs
    the rest of the app in a task of its own, and a context variable set
    either side of that boundary is a coin toss.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            # Lifespan and websockets. Neither is a request, and neither has
            # a response to hang a header off.
            await self.app(scope, receive, send)
            return

        inbound = Headers(scope=scope).get(REQUEST_ID_HEADER)
        # An id handed in is kept, so a caller that already has a trace sees
        # the same id on both sides instead of the two logs inventing their
        # own. gary-web mints one before the browser can choose it.
        request_id = inbound or uuid.uuid4().hex
        started = time.perf_counter()
        seen: dict[str, int] = {}

        async def tagged(message: Message) -> None:
            if message["type"] == "http.response.start":
                seen["status"] = message["status"]
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        def elapsed() -> float:
            return round((time.perf_counter() - started) * 1000, 3)

        with bind(request_id=request_id):
            try:
                await self.app(scope, receive, tagged)
            except Exception:
                # Logged here so the failure carries the request id. Outside
                # this block the context is gone and the 500 is an orphan.
                logger.exception(
                    "http.request",
                    method=scope["method"],
                    path=scope["path"],
                    status=500,
                    duration_ms=elapsed(),
                )
                raise

            logger.info(
                "http.request",
                method=scope["method"],
                path=scope["path"],
                status=seen["status"],
                duration_ms=elapsed(),
            )
