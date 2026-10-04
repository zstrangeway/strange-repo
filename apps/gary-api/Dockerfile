FROM python:3.14-slim AS builder

RUN pip install --no-cache-dir uv==0.8.17

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Dependencies first, so a source-only change does not re-resolve the lockfile.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project --no-dev

COPY src ./src
RUN uv sync --locked --no-dev


FROM python:3.14-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Needed by the release_command, which runs migrations before the new version
# takes traffic.
COPY alembic.ini ./
COPY migrations ./migrations

ENV PATH="/app/.venv/bin:$PATH"

# The commit this image was built from, reported by /health. Passed in from
# the deploy workflow: only apps/gary-api reaches the build context, so there
# is no .git here to read a version out of. Empty locally, which /health
# reports as "unknown" rather than pretending to a version it does not have.
ARG RELEASE=""
ENV RELEASE=$RELEASE

# Say which of the two happened. An image that cannot name its own build looks
# exactly like one that can until the day you need it to.
RUN if [ -n "$RELEASE" ]; then \
      echo "Release: this image reports itself as $RELEASE"; \
    else \
      echo "Release: NO release stamp — /health will report version=unknown"; \
    fi

# Start the application, not merely install it. Without this the whole of
# this image's gate is "docker build succeeded", and an image that cannot run
# gary-api passes it — which is not hypothetical: the python 3.14 bump was
# green on all five checks while shipping an image where this exact import
# raises, because pydantic asserts on 3.14's ForwardRef shape. Every route
# would have been unreachable and Fly's health check would have been the
# first thing to notice.
#
# The import is enough. It builds every Pydantic model in play.py and every
# route on the app, which is where that class of failure lands. It needs no
# database — the engine is created lazily and the lifespan does not run — so
# this stays a build step rather than something needing a service.
#
# /health by name rather than a count of routes: a hollow app with the
# framework's own /docs and /openapi.json on it would satisfy a count, and a
# check that passes on nothing is the thing this file keeps being bitten by.
RUN python -c "from gary_api.app import app; paths = {getattr(route, 'path', None) for route in app.routes}; assert '/health' in paths, f'no /health among {sorted(p for p in paths if p)}'; print(f'Starts: imported gary_api.app, {len(app.routes)} routes, /health present')"

EXPOSE 8080

# 0.0.0.0 is the address fly-proxy expects, and it is what Flycast routes to.
# Binding :: instead left the app unreachable and failed the deploy's smoke
# check. Private networking is the proxy's job, not this socket's.
CMD ["fastapi", "run", "src/gary_api/app.py", "--host", "0.0.0.0", "--port", "8080"]
