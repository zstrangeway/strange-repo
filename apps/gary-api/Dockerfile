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

# Needed by the release_command, which runs migrations before the new version
# takes traffic.
COPY alembic.ini ./
COPY migrations ./migrations

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

# 0.0.0.0 is the address fly-proxy expects, and it is what Flycast routes to.
# Binding :: instead left the app unreachable and failed the deploy's smoke
# check. Private networking is the proxy's job, not this socket's.
CMD ["fastapi", "run", "src/gary_api/app.py", "--host", "0.0.0.0", "--port", "8080"]
