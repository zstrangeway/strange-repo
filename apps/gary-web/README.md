# gary-web

A Next.js companion to gary-api. It signs people up and in, and welcomes them
home by name.

gary-web owns the session: an httpOnly cookie on **its own** origin holding a
gary-api token, and every gary-api call is made from gary-web's server. A
cookie set by gary-api would be third-party here and dropped by Safari and
Firefox, so this is not a style choice.

**Those calls do not appear in browser devtools.** You will see gary-web's own
Server Action request and nothing else; the gary-api call is in the gary-web
server log.

## Run

```sh
pnpm install     # once, from the repo root
pnpm dev         # development
pnpm build       # production build
pnpm serve       # production server
```

Set `GARY_API_URL` to point at gary-api. It defaults to `http://127.0.0.1:8000`.

## Test

Behavior is specified in Gherkin and run with cucumber-js against a real
Chromium via Playwright. The suite starts its own Next server and a stub
gary-api, so nothing needs to be running first.

```sh
pnpm test          # against the stub, fast
pnpm test:e2e      # against a real gary-api and a throwaway database
```

`test:e2e` needs a reachable Postgres (`DATABASE_URL`) and gary-api's Python
toolchain, because it boots the real thing. It creates `gary_e2e_<random>`,
migrates it, empties it between scenarios and drops it at the end.

The stub is fast and covers almost everything, but it was written from the same
understanding that produced gary-api, so it cannot notice the two drifting
apart — that is the whole reason `test:e2e` exists. Keep it small; it is there
to catch drift, not to cover behaviour.

The specs need a Playwright browser. Either install one:

```sh
pnpm exec playwright install chromium
```

or, on a machine that already has a Chromium that Playwright did not install,
point at it directly:

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chromium pnpm test
```
