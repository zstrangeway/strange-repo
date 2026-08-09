# Build context is the repo root, so the pnpm workspace and lockfile are visible.
#   docker build -f apps/example-web/Dockerfile .

FROM node:22-alpine AS base
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable

# --- deps: install from the lockfile only, so this layer caches on lockfile changes
FROM base AS deps
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY apps/example-web/package.json apps/example-web/
COPY apps/example-api/package.json apps/example-api/
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile --filter example-web...

# --- builder: compile the Next.js standalone bundle
FROM base AS builder
WORKDIR /repo
COPY --from=deps /repo ./
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter example-web build

# --- runner: only the standalone output, no package manager, no node_modules tree
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=8080
ENV HOSTNAME=0.0.0.0

RUN addgroup -g 1001 -S nodejs && adduser -u 1001 -S nextjs -G nodejs

# server.js and its traced node_modules, then the assets it serves itself.
COPY --from=builder --chown=nextjs:nodejs /repo/apps/example-web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /repo/apps/example-web/.next/static ./apps/example-web/.next/static

USER nextjs
EXPOSE 8080

CMD ["node", "apps/example-web/server.js"]
