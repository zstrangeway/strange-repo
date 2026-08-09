from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="gary-api")

# gary-web reads /health from the browser, so the request is cross-origin.
# The endpoint is unauthenticated and read-only, so any origin may ask.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
