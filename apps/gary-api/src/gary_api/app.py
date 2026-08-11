import os
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gary_api import auth, db, dice, identity, logs, play
from gary_api.identity import consent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # uvicorn configures its own loggers and leaves the root one alone, so
    # without this every record this app emits below WARNING is dropped.
    logs.configure()
    identity.report_configuration()
    # Seeded only when the environment says to, which is how a spec asserts a
    # number rather than merely that a number arrived.
    dice.configure()
    yield


DEFAULT_ORIGINS = "http://localhost:3000"

# What gary-web puts the correlation id in. Named here rather than repeated
# as a string, because the middleware and the logging layer must agree.
REQUEST_ID_HEADER = "x-request-id"


def browser_origins() -> list[str]:
    """Where a browser may call this API from.

    A deployment's business, not a default: gary-web runs entirely in the
    browser now, so this list is the difference between it working and the
    browser refusing to hand it the answer.
    """
    raw = os.environ.get("BROWSER_ORIGINS", DEFAULT_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app() -> FastAPI:
    """Built by a function so the specs can stand one up with other origins.

    Middleware is fixed when the app is built, so a scenario that changes
    which origins are allowed has to build a new one.
    """
    app = FastAPI(title="gary-api", lifespan=lifespan)

    # Outermost of ours, so the request id is bound before anything else can
    # log.
    app.add_middleware(logs.RequestContext)

    # Named origins rather than "*": the answer to a signed-in request is
    # somebody's account, and any page on the internet should not be able to
    # ask for it. No allow_credentials, because gary-api takes a bearer token
    # and never a cookie — there is nothing for a browser to send along.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=browser_origins(),
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        # x-request-id is not optional here: gary-web sends it on every call
        # so both logs record the same id, and a header a browser is not told
        # it may send turns every call into a refused preflight.
        allow_headers=["authorization", "content-type", REQUEST_ID_HEADER],
    )

    # HTTPException serialises its detail and nothing else, so a refusal's
    # code needs saying explicitly. Registered here rather than in auth so the
    # shape of an error response is decided in one place for the whole app.
    app.add_exception_handler(auth.Refusal, _render_refusal)

    app.include_router(auth.router)
    app.include_router(play.router)
    # 404s unless IDENTITY_FAKE is on, so mounting it always is safe.
    app.include_router(consent.router)
    app.add_api_route("/health", health, methods=["GET"])

    return app


async def _render_refusal(_request: Request, error: Exception) -> JSONResponse:
    refusal = cast(auth.Refusal, error)
    return JSONResponse(
        status_code=refusal.status_code,
        content={"detail": refusal.detail, "code": refusal.code},
    )


async def health() -> dict[str, str]:
    # Always 200: the app answering is itself the signal that it is up, and
    # the body carries the state of what it depends on. A non-200 here would
    # also fail Fly's health check and block deploys during a database outage.
    reachable = await db.is_reachable()

    return {
        "status": "ok" if reachable else "degraded",
        "database": "ok" if reachable else "unavailable",
    }


app = create_app()
