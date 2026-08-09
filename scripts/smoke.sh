#!/usr/bin/env bash
# Post-deploy check: confirm each deployed app is actually serving.
#
# Fly's own health checks gate the release, but they only prove the container
# answers /health. This additionally exercises a real route per app, so a
# deploy that boots but serves nothing useful still fails the pipeline.
#
# Usage: scripts/smoke.sh <api-base-url> <web-base-url>

set -euo pipefail

API_URL="${1:?usage: smoke.sh <api-base-url> <web-base-url>}"
WEB_URL="${2:?usage: smoke.sh <api-base-url> <web-base-url>}"

RETRIES="${SMOKE_RETRIES:-30}"
DELAY="${SMOKE_DELAY:-2}"

fail() {
  echo "::error::$*" >&2
  exit 1
}

# Machines may be stopped (auto_stop_machines), so the first request has to
# wake one — retry rather than failing on the cold start.
wait_for_ok() {
  local url="$1" code=""
  for _ in $(seq 1 "$RETRIES"); do
    code=$(curl -fsS -o /dev/null -w '%{http_code}' --max-time 10 "$url" 2>/dev/null || true)
    [ "$code" = "200" ] && return 0
    sleep "$DELAY"
  done
  fail "$url never returned 200 (last status: ${code:-none})"
}

body_contains() {
  local url="$1" expected="$2" body
  body=$(curl -fsS --max-time 10 "$url")
  case "$body" in
    *"$expected"*) ;;
    *) fail "$url did not contain '$expected'. Got: $body" ;;
  esac
}

echo "==> $API_URL"
wait_for_ok "$API_URL/health"
body_contains "$API_URL/health" '"status":"ok"'
body_contains "$API_URL/greet?name=Zac" 'Hello, Zac!'

echo "==> $WEB_URL"
wait_for_ok "$WEB_URL/health"
body_contains "$WEB_URL/health" '"status":"ok"'
body_contains "$WEB_URL/" 'Hello, world!'

echo "smoke tests passed"
