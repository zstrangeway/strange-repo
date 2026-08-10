from contextlib import asynccontextmanager

from fastapi import FastAPI

from gary_api import auth, db, identity, logs
from gary_api.identity import consent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # uvicorn configures its own loggers and leaves the root one alone, so
    # without this every record this app emits below WARNING is dropped.
    logs.configure()
    identity.report_configuration()
    yield


app = FastAPI(title="gary-api", lifespan=lifespan)

# Outermost of ours, so the request id is bound before anything else can log.
app.add_middleware(logs.RequestContext)

# No CORS middleware yet: gary-web still calls this from its own server, so
# nothing in a browser talks to gary-api directly. That changes the day a
# browser client calls it, and this is the line that has to change with it.

app.include_router(auth.router)
# 404s unless IDENTITY_FAKE is on, so mounting it always is safe.
app.include_router(consent.router)


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
