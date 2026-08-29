# syntax=docker/dockerfile:1
# The syntax line is load-bearing: RUN --mount=type=secret below needs it.

# Build context is the repository root: the pnpm workspace has to be intact
# for the app's dependencies to resolve.
FROM node:26-slim AS base

ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

RUN corepack enable


FROM base AS deps

WORKDIR /repo

# Manifests only, so a source-only change reuses the installed dependencies.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/gary-api/package.json apps/gary-api/
COPY apps/gary-web/package.json apps/gary-web/
COPY packages/ui/package.json packages/ui/

RUN pnpm install --frozen-lockfile


FROM base AS builder

WORKDIR /repo

# sentry-cli is a Rust binary that verifies TLS against the system trust store.
# node:22-slim ships without one, and Node carries its own roots, so the app's
# HTTPS worked while the source map upload died on "unable to get local issuer
# certificate" — invisible until the plugin was unmuted. Builder stage only:
# nothing in the running image needs this.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY --from=deps /repo/ ./
COPY apps/gary-web apps/gary-web
# The shared component library is compiled from source by `next build`
# (transpilePackages), so the sources have to be in the build context too.
COPY packages/ui packages/ui

# Sentry's browser DSN has to be here rather than in `fly secrets`: NEXT_PUBLIC_
# variables are inlined into the client bundle by `next build`, so a value that
# only exists at runtime never reaches the browser and client-side reporting
# stays silently off. Supplied by [build.args] in fly.toml. Safe to bake in — a
# DSN is public by design and ships in the bundle either way.
ARG NEXT_PUBLIC_SENTRY_DSN=""
ENV NEXT_PUBLIC_SENTRY_DSN=$NEXT_PUBLIC_SENTRY_DSN

# Where gary-api answers, for the same reason and with the same consequence:
# this app runs in the browser, so a value supplied at runtime arrives long
# after the only moment it could have mattered. Wrong here and every call goes
# to the wrong host with nothing in the server log to say so.
ARG NEXT_PUBLIC_GARY_API_URL="https://gary-api.fly.dev"
ENV NEXT_PUBLIC_GARY_API_URL=$NEXT_PUBLIC_GARY_API_URL

# Which Sentry project the source maps belong to. Not secret, and not a
# runtime concern — sentry-cli only needs them while the bundle is being built.
ARG SENTRY_ORG=""
ARG SENTRY_PROJECT=""
ENV SENTRY_ORG=$SENTRY_ORG \
    SENTRY_PROJECT=$SENTRY_PROJECT

# The release the maps are filed under. Only apps/gary-web is copied into the
# build context, so there is no .git here for sentry-cli to read a version
# from — left alone it uploads against `--release undefined`, which matches
# none of the events the running app reports. Passed in from CI as the commit
# SHA so both sides agree. Empty locally, which just skips the release.
ARG SENTRY_RELEASE=""
ENV SENTRY_RELEASE=$SENTRY_RELEASE

# Say which of the two happened. A build that quietly produces an image with no
# browser error reporting looks exactly like one that works.
RUN if [ -n "$NEXT_PUBLIC_SENTRY_DSN" ]; then \
      echo "Sentry: browser DSN baked into the client bundle"; \
    else \
      echo "Sentry: NO browser DSN — client-side errors will NOT be reported"; \
    fi

# The auth token arrives as a BuildKit secret rather than an ARG: build args
# are readable in image history forever, and this one is a real credential
# unlike the DSN. Absent, the build still succeeds and simply skips upload —
# which is what every local build and the CI smoke build do.
RUN --mount=type=secret,id=sentry_auth_token \
    if [ -s /run/secrets/sentry_auth_token ] && [ -n "$SENTRY_ORG" ] && [ -n "$SENTRY_PROJECT" ]; then \
      echo "Sentry: uploading source maps to $SENTRY_ORG/$SENTRY_PROJECT" \
           "as release ${SENTRY_RELEASE:-<none — maps will not match events>}"; \
      export SENTRY_AUTH_TOKEN="$(cat /run/secrets/sentry_auth_token)"; \
    else \
      echo "Sentry: NOT uploading source maps — production stack traces will be minified"; \
      echo "        token=$([ -s /run/secrets/sentry_auth_token ] && echo yes || echo no)" \
           "org=${SENTRY_ORG:-unset} project=${SENTRY_PROJECT:-unset}"; \
    fi; \
    pnpm --filter gary-web exec next build


FROM base AS runner

WORKDIR /repo

ENV NODE_ENV=production \
    PORT=8080 \
    HOSTNAME=0.0.0.0

# The standalone bundle carries its own node_modules and expects to be run
# from the workspace root, with static assets restored alongside it.
COPY --from=builder /repo/apps/gary-web/.next/standalone ./
COPY --from=builder /repo/apps/gary-web/.next/static ./apps/gary-web/.next/static
COPY --from=builder /repo/apps/gary-web/public ./apps/gary-web/public

EXPOSE 8080

CMD ["node", "apps/gary-web/server.js"]
