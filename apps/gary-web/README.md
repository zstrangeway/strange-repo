# gary-web

A Next.js companion to gary-api. It signs people up and in, and welcomes them
home by name.

It runs entirely in the browser. There is no server rendering and no server
of its own: every route is static, every call to gary-api is made from the
page, and the session is a gary-api token in `localStorage`.

That is a trade, not a free win. The token is readable by any script on the
page, so an XSS bug is a stolen session rather than a defaced one — the price
of having no server to hold an httpOnly cookie.

**Two things follow that will otherwise waste your time.** gary-api must name
this app's origin in `BROWSER_ORIGINS` or the browser makes every call and
then refuses to hand back the answer. And gary-web's own log lines are in the
browser console, not in any server log — nobody collects them.

## Run

```sh
pnpm install     # once, from the repo root
pnpm dev         # development
pnpm build       # production build
pnpm serve       # production server
```

Set `NEXT_PUBLIC_GARY_API_URL` to point at gary-api. It defaults to
`http://127.0.0.1:8000`.

It is baked into the bundle by `next build` rather than read at runtime,
because a browser has no environment to read. Setting it on the running app
changes nothing; it has to be a build arg, and the Dockerfile takes one.

## Test

Behavior is specified in Gherkin and run with cucumber-js against a real
Chromium via Playwright. The suite starts its own Next server and a stub
gary-api, so nothing needs to be running first.

```sh
pnpm unit          # src/lib only, with its coverage gate
pnpm test          # the above, then the browser specs against the stub
pnpm test:e2e      # against a real gary-api and a throwaway database
```

`pnpm unit` is Vitest over **`src/lib` and nothing else**, gated at 100%
including branches. That scope is deliberate: everything outside `src/lib` here
is a React component, and [Next's own testing
guide](https://nextjs.org/docs/app/guides/testing) recommends covering those
end to end rather than with unit tests. A gate that swept them in would report
a number it had not earned. `src/lib` is plain modules, which is where the
branchy logic — error mapping, empty bodies, token handling — actually lives.

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
