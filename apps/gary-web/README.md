# gary-web

A Next.js companion to gary-api. The home page server-renders gary-api's
`/health` response on each request, and shows `unavailable` when the API cannot
be reached.

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
pnpm test
```

The specs need a Playwright browser. Either install one:

```sh
pnpm exec playwright install chromium
```

or, on a machine that already has a Chromium that Playwright did not install,
point at it directly:

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chromium pnpm test
```
