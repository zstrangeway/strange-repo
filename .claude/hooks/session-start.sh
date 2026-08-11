#!/bin/bash
#
# Gets a Claude Code on the web session to the point where `pnpm test` means
# something. Without it the container has the toolchains but no dependencies
# and no running database, so gary-api's specs fail on connection refused and
# the first thing every session does is rediscover that.
#
# Reports what it did. A setup step that silently does nothing is worse than
# no setup step: the suite still fails, but now it fails somewhere further
# from the cause.
#
# Idempotent — safe on startup, resume, clear and compact alike.

set -euo pipefail

# Local machines have their own Postgres and their own opinions about it.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  echo "session-start: local session, leaving the environment alone"
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"
echo "session-start: preparing $(pwd)"

# ---------------------------------------------------------------- javascript
# install rather than a frozen install: the container is cached after this
# runs, so the store is warm next time, and a lockfile drift should surface as
# a diff rather than as a hook that refuses to start the session.
echo "session-start: pnpm install"
pnpm install --silent
echo "session-start: pnpm workspace ready"

# @go-task/cli downloads its binary on first use rather than at install time,
# and every script in this repo goes through task. Warming it here means the
# download happens once, into the cached container, instead of in front of the
# first `pnpm test` of every session — or failing outright in one whose egress
# is restricted.
echo "session-start: warming the task runner"
pnpm exec task --version >/dev/null
echo "session-start: task $(pnpm exec task --version) ready"

# -------------------------------------------------------------------- python
echo "session-start: uv sync (gary-api)"
(cd apps/gary-api && uv sync --quiet)
echo "session-start: gary-api virtualenv ready"

# ------------------------------------------------------------------ postgres
# gary-api's specs run against a real Postgres on purpose — the healthy and
# the unreachable paths are both genuine — so one has to be listening.
database_ready=no

if command -v pg_lsclusters >/dev/null 2>&1; then
  version="$(pg_lsclusters -h 2>/dev/null | awk 'NR==1 {print $1}')"
  cluster="$(pg_lsclusters -h 2>/dev/null | awk 'NR==1 {print $2}')"

  if [ -n "${version:-}" ] && [ -n "${cluster:-}" ]; then
    hba="/etc/postgresql/${version}/${cluster}/pg_hba.conf"

    # The repo's default DATABASE_URL carries no password, so local TCP has to
    # be trusted or every connection fails authentication. This is a throwaway
    # container with a loopback-only server; it is not a posture to copy.
    if [ -f "$hba" ]; then
      sed -i -E \
        -e 's|^(host[[:space:]]+all[[:space:]]+all[[:space:]]+127\.0\.0\.1/32[[:space:]]+).*|\1trust|' \
        -e 's|^(host[[:space:]]+all[[:space:]]+all[[:space:]]+::1/128[[:space:]]+).*|\1trust|' \
        "$hba"
    fi

    if pg_lsclusters -h | awk -v c="$cluster" '$2==c {print $4}' | grep -q online; then
      pg_ctlcluster "$version" "$cluster" reload || true
      echo "session-start: postgres ${version}/${cluster} already online"
    else
      pg_ctlcluster "$version" "$cluster" start
      echo "session-start: postgres ${version}/${cluster} started"
    fi

    for _ in $(seq 1 30); do
      if pg_isready -h 127.0.0.1 -q 2>/dev/null; then
        database_ready=yes
        break
      fi
      sleep 1
    done
  fi
fi

if [ "$database_ready" = yes ]; then
  echo "session-start: postgres reachable on 127.0.0.1:5432"
  echo "session-start: alembic upgrade head"
  (cd apps/gary-api && uv run --quiet alembic upgrade head >/dev/null)
  echo "session-start: gary-api schema at head"
else
  # Not fatal: gary-web's own specs and the ui package need no database, and a
  # session that starts with two thirds of its suite working beats one that
  # will not start at all. Said loudly because the third that does not work
  # fails on connection refused, which reads like a bug in the app.
  echo "session-start: WARNING — no Postgres. gary-api specs and pnpm test will"
  echo "session-start: WARNING   fail on connection refused. gary-web unit and"
  echo "session-start: WARNING   browser specs, and @gary/ui, are unaffected."
fi

echo "session-start: done"
