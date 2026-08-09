# Build context is the repository root: the pnpm workspace has to be intact
# for the app's dependencies to resolve.
FROM node:22-slim AS base

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

RUN pnpm install --frozen-lockfile


FROM base AS builder

WORKDIR /repo

COPY --from=deps /repo/ ./
COPY apps/gary-web apps/gary-web

# Sentry's browser DSN has to be here rather than in `fly secrets`: NEXT_PUBLIC_
# variables are inlined into the client bundle by `next build`, so a value that
# only exists at runtime never reaches the browser and client-side reporting
# stays silently off. Supplied by [build.args] in fly.toml. Safe to bake in — a
# DSN is public by design and ships in the bundle either way.
ARG NEXT_PUBLIC_SENTRY_DSN=""
ENV NEXT_PUBLIC_SENTRY_DSN=$NEXT_PUBLIC_SENTRY_DSN

# Say which of the two happened. A build that quietly produces an image with no
# browser error reporting looks exactly like one that works.
RUN if [ -n "$NEXT_PUBLIC_SENTRY_DSN" ]; then \
      echo "Sentry: browser DSN baked into the client bundle"; \
    else \
      echo "Sentry: NO browser DSN — client-side errors will NOT be reported"; \
    fi

RUN pnpm --filter gary-web exec next build


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
