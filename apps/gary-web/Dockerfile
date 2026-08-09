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
