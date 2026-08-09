FROM python:3.11-slim AS builder

RUN pip install --no-cache-dir uv==0.8.17

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Dependencies first, so a source-only change does not re-resolve the lockfile.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project --no-dev

COPY src ./src
RUN uv sync --locked --no-dev


FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

# Bind ::, not 0.0.0.0. Fly's private network — everything .internal resolves
# to — is IPv6-only, and an IPv4 socket cannot accept those connections. A
# dual-stack :: socket still serves IPv4, so the public route is unaffected.
CMD ["fastapi", "run", "src/gary_api/app.py", "--host", "::", "--port", "8080"]
