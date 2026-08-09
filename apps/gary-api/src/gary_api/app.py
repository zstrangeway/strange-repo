from contextlib import asynccontextmanager

from fastapi import FastAPI

from gary_api import auth, db, logs, mail


@asynccontextmanager
async def lifespan(app: FastAPI):
    # uvicorn configures its own loggers and leaves the root one alone, so
    # without this every record this app emits below WARNING is dropped —
    # including the reset link the console mail provider exists to print.
    logs.configure()
    mail.report_configuration()
    yield


app = FastAPI(title="gary-api", lifespan=lifespan)

# Outermost of ours, so the request id is bound before anything else can log.
app.add_middleware(logs.RequestContext)

# No CORS middleware: nothing in a browser talks to gary-api any more.
# gary-web calls it from its own server so that the session cookie belongs to
# gary-web's origin — a cookie set here would be third-party to gary-web and
# dropped by Safari and Firefox. /health is left to Fly's checker, which is
# not a browser either.

app.include_router(auth.router)


@app.get("/health")
async def health() -> dict[str, str]:
    # Always 200: the app answering is itself the signal that it is up, and
    # the body carries the state of what it depends on. A non-200 here would
    # also fail Fly's health check and block deploys during a database outage.
    reachable = await db.is_reachable()

    return {
        "status": "ok" if reachable else "degraded",
        "database": "ok" if reachable else "unavailable",
    }
