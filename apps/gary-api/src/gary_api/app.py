from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gary_api import db, mail


@asynccontextmanager
async def lifespan(app: FastAPI):
    mail.report_configuration()
    yield


app = FastAPI(title="gary-api", lifespan=lifespan)

# gary-web reads /health from the browser, so the request is cross-origin.
# The endpoint is unauthenticated and read-only, so any origin may ask.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
)


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
