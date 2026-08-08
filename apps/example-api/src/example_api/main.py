"""FastAPI application entrypoint."""

from fastapi import FastAPI

from example_api import __version__
from example_api.greeting import greet

app = FastAPI(title="example-api", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the service is up."""
    return {"status": "ok", "version": __version__}


@app.get("/greet")
def greeting(name: str | None = None) -> dict[str, str]:
    """Greet the caller by name, or the world when no name is given."""
    return {"message": greet(name)}
