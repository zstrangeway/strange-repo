from gary_api.app import app

__all__ = ["app"]


def main() -> None:
    import uvicorn

    uvicorn.run("gary_api.app:app", host="127.0.0.1", port=8000, reload=True)
