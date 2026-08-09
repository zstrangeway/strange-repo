# Build context is the repo root, for symmetry with example-web.
#   docker build -f apps/example-api/Dockerfile .

FROM python:3.11-slim AS builder
# Pinned uv from PyPI rather than COPY --from=ghcr.io/astral-sh/uv, so the build
# needs only one registry and works where ghcr.io is restricted.
RUN pip install --no-cache-dir uv==0.8.17

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Resolve dependencies before copying source, so edits don't bust this layer.
COPY apps/example-api/pyproject.toml apps/example-api/uv.lock ./
RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY apps/example-api/src ./src
RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# --- runtime: the virtualenv only, no uv and no build tooling
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH=/app/.venv/bin:$PATH
ENV PORT=8080

RUN useradd --create-home --uid 1001 appuser

WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

USER appuser
EXPOSE 8080

CMD ["sh", "-c", "uvicorn example_api.main:app --host 0.0.0.0 --port ${PORT}"]
