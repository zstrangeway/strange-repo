# strange-repo

A pnpm + uv monorepo. It builds **gary**, an AI game master named for Gary
Gygax: pick a system and a module, make a party, and play a tabletop campaign
in chat.

| App | Stack | What it is |
| --- | --- | --- |
| [`apps/gary-api`](apps/gary-api) | FastAPI + Postgres | The game — dice, rules, world and narration — plus accounts and sessions |
| [`apps/gary-web`](apps/gary-web) | Next.js | The table: campaigns, characters, and a turn as it is written |

Play is divided into **scenes**, which are the unit of gary's memory: the
model is told the current scene and a recap of each one before it, so a long
campaign does not cost more every turn forever. Closing a scene is also where
the world is reconciled — the last moment something narrated but never
recorded can still be recorded.

The design worth knowing before reading either: **the model narrates and
decides nothing.** Dice, the rules of the system being run, and the state of
the world are deterministic engines, and the model asks them rather than
asserting over them. That is what stops the story drifting and stops gary
inventing the number that decides what happens. See
[`apps/gary-api`](apps/gary-api#the-game).

## Why one repo

gary could live on its own; the scaffolding around it is the reason it does
not. [`packages/ui`](packages/ui) is one set of components rather than one per
app, every app is specified in Gherkin and gated the same way so `pnpm test`
means the same thing wherever it is run, [`CLAUDE.md`](CLAUDE.md) is one file
rather than a set of conventions re-explained per project, and one workflow
tests, builds and deploys everything. That is most of what starting a project
actually costs, and it is the part an agent otherwise rebuilds — slightly
differently each time — before it writes a line of the thing you asked for.
Here it is already decided, so the next thing built starts at its first real
feature.

## Running it

From a fresh clone to gary in a browser. You need **Node 22**, **pnpm 10**,
[**uv**](https://docs.astral.sh/uv/) for gary-api's Python, and a **Postgres
16** you can reach. Nothing here runs in Docker.

```sh
pnpm install     # once, from this directory
```

Three variables matter locally. The first two are switches, standing in for the
things this repo holds no credentials for; the third has a default worth
knowing:

| Variable | | |
| --- | --- | --- |
| `IDENTITY_FAKE=1` | gary-api | Stands in for Google, Facebook and Apple. Without it the sign-in page has no buttons at all — nothing here has their client secrets, and a button that cannot work is worse than no button. |
| `GM_FAKE=1` | gary-api | Stands in for the model, so a turn costs nothing. Set `OPENROUTER_API_KEY` instead to play against a real one. |
| `DATABASE_URL` | gary-api | Defaults to `postgresql://postgres@127.0.0.1:5432/postgres`. Set it if yours is not that. |

Create the schema and the local accounts:

```sh
pnpm --filter gary-api seed
```

It migrates first, then prints a sign-in code per account. Those codes are what
you paste into the stand-in provider's page, so keep the output.

Then a terminal each:

```sh
IDENTITY_FAKE=1 GM_FAKE=1 pnpm --filter gary-api dev     # http://127.0.0.1:8000
```

```sh
pnpm --filter gary-web dev                               # http://localhost:3000
```

Open **`http://localhost:3000`, not `127.0.0.1:3000`.** They are different
origins to a browser, and gary-api answers only the ones named in
`BROWSER_ORIGINS` — which defaults to `http://localhost:3000` alone. From the
other spelling every call is made and then refused on the way back, so the page
renders with no sign-in buttons and the reason is only in the console.

Sign in with any of the three, paste one of the codes `seed` printed, and you
land on your campaigns. Starting one picks a system, a module and a model, and
`GM_FAKE=1` narrates it without spending anything.

gary-web finds gary-api at `NEXT_PUBLIC_GARY_API_URL`, default
`http://127.0.0.1:8000`. It is read when the app is built rather than when it
runs, so changing it means restarting `dev`.

## Working on it

```sh
pnpm test        # every app's specs
```

[`BACKLOG.md`](BACKLOG.md) is what is known to be wrong or thin and not yet
done. Things deliberately not built are not in it — those are in the app
READMEs, marked ⚠️, beside the code that would change if they ever were.
[`proposals/`](proposals) is Gherkin waiting to be agreed, held outside the
apps' `features/` trees because both runners fail on an undefined step.

### The three tiers

`pnpm test` runs the first two. They need no setup beyond a Postgres for
gary-api.

- **gary-api specs** — Gherkin through behave, in-process against the ASGI app
  and a real Postgres. Everything is real except the network. Alongside them,
  stdlib unittest for what the API cannot reach. Gated at 100%.
- **gary-web specs** — Gherkin through Cucumber, in a real browser against a
  real `next dev`, with gary-api replaced by an in-memory stub. Alongside them,
  Vitest over `src/lib` only, gated at 100%.
- **end to end** — the same browser, against a **real gary-api** on a database
  created and dropped for the run.

```sh
pnpm --filter gary-web test:e2e
```

The third tier exists because the first two can both be green while gary is
broken: the stub was written from the same understanding that produced
gary-api, so it cannot notice the two drifting apart. Rename a field in
gary-api's sign-in response and every spec in the first two tiers still
passes. It is deliberately few — it costs a Postgres and a Python
process, and its job is to catch drift, not to cover behaviour.

**No tier ever calls a real model**, including the third — the same trade made
for Google and Facebook, and for the same reasons. `pnpm --filter gary-api
smoke` plays one real turn and prints what the model actually did with the
tools, which is the only way to see that gap. It is opt-in and never runs on
its own, because it spends somebody's tokens.

gary-web's coverage gate covers `src/lib` and nothing else, deliberately. The
rest of that app is React components, and [Next's own
testing guide](https://nextjs.org/docs/app/guides/testing) says to cover those
end to end rather than with unit tests. A gate that swept them in would report
a number it had not earned; the Gherkin suites are what cover them.

Ephemeral means the database, not the server: the run creates
`gary_e2e_<random>` on whatever `DATABASE_URL` points at, migrates it with the
real Alembic migrations, empties it between scenarios, and drops it at the
end. So it needs no Docker, and works against a local Postgres or a CI service
container alike. The providers are still stood in for, but by gary-api's own
stand-in rather than the suite's — a real page at a real URL that the browser
navigates to and back from, exactly as it would with Google.

Per-app commands live in each app's `Taskfile.yml` and are reachable as
`pnpm --filter <app> <script>`, or `pnpm exec task --list` to see them all.

## Logs

Both apps write structured logs: one JSON object per line, the same field
names on both sides.

```json
{"timestamp":"2026-08-09T17:50:00.123Z","level":"info","logger":"api",
 "message":"api.call","app":"gary-web","request_id":"5f2c…","status":200}
```

`message` is a stable event name — `api.call`, `mail.logged`, `http.request` —
and whatever varies goes beside it as a field, so a search can filter rather
than grep. An exception lands as an `error` object with `type`, `message` and
`stack`, inside the same line rather than as a loose traceback after it.

| Variable | Applies to | Default | |
| --- | --- | --- | --- |
| `LOG_LEVEL` | both | `INFO` | |
| `LOG_FORMAT` | gary-api | `json` | `text` lays the same fields out for reading by eye |

`gary_api/logs.py` configures the *root* logger, so uvicorn's and SQLAlchemy's
records come out in the same shape as ours rather than only ours.

### Following one request through both apps

gary-web mints a request id for each call it makes and sends it as
`x-request-id`; gary-api keeps an inbound id rather than minting its own, binds
it for the length of the request, and puts it on every line logged during it —
including lines from libraries that know nothing about any of this. One id
therefore finds one user action in both logs.

The id is minted per call, in the browser, because there is no request to bind
one to any more. Several calls behind one click therefore carry different ids —
what survives is the pairing of each call with gary-api's record of it.

**gary-web's log lines are in the browser console, and nobody collects them.**
That is a real loss and the reason the shape is kept anyway: an id read off a
console still finds its other half in gary-api's log. It also means gary-api
records whatever id it is handed, and a browser is what hands it over.

## Deploying

Both apps deploy to [Fly.io](https://fly.io) from `.github/workflows/ci.yml` on
every push to `main`. Pull requests run the specs and build both images, but
never deploy.

### One-time setup

Add a Fly deploy token to the repository as the `FLY_API_TOKEN` secret, and the
workflow does the rest — it creates each app on the first run if it does not
already exist, then deploys. Nothing needs running by hand.

Fly app names are globally unique, so `gary-api` and `gary-web` may already be
taken. If either is, change `app` in that app's `fly.toml` and the matching
name in the workflow's `Ensure the Fly app exists` step — and for gary-api,
`NEXT_PUBLIC_GARY_API_URL` in `apps/gary-web/Dockerfile` and `BROWSER_ORIGINS`
in `apps/gary-api/fly.toml`, since those two name each other.

Apps are created in the `FLY_ORG` organisation set at the top of the workflow,
which defaults to `personal`.

Fly resolves the two paths against different bases, which is worth knowing
before editing either `fly.toml`:

- the config path is relative to the **working directory**
- `build.dockerfile` inside it is relative to **the config file's own directory**

The build context is the working directory. gary-web therefore deploys from the
repo root with `--config apps/gary-web/fly.toml` and `dockerfile = "Dockerfile"`
— it cannot build from `apps/gary-web`, because its image needs
`pnpm-lock.yaml`, `pnpm-workspace.yaml`, and the root `package.json` in the
context for the workspace to resolve.

gary-api needs a Postgres. It runs on Fly Managed Postgres:

```sh
flyctl mpg create
flyctl mpg attach <cluster-id> -a <gary-api-app-name>
```

`attach` sets `DATABASE_URL` as a secret, which is the only coupling — any
Postgres works, and `database_url()` normalises whatever connection string a
provider hands out. Worth knowing that Fly Managed Postgres costs an order of
magnitude more than the two apps combined, so a hosted free tier or a self-run
Postgres app is a cheap swap if that ever matters.

Then add a deploy token to the repository as the `FLY_API_TOKEN` secret:

```sh
flyctl tokens create deploy --name github-actions
```

### How the two apps find each other

The browser talks to both. gary-web is a static app, so every call to gary-api
is made from the page, and gary-api must be publicly reachable.

Two settings have to agree, and neither says anything useful when they do not:

- `NEXT_PUBLIC_GARY_API_URL` — where gary-web looks for gary-api. Inlined by
  `next build`, so it is a **build arg** in `apps/gary-web/Dockerfile`. Setting
  it on the running app changes nothing; a browser has no environment to read.
- `BROWSER_ORIGINS` — the origins gary-api answers, in `apps/gary-api/fly.toml`.
  Named rather than `*`, because the answer to a signed-in request is somebody's
  account.

Get either wrong and the app renders nothing at all, with the reason only in
the browser console. It is the first thing to check when a deploy looks blank.

The session is a gary-api token in `localStorage`, not a cookie. A cookie set
by gary-api would be third-party to gary-web and dropped by Safari and Firefox
— `fly.dev` is on the public suffix list, so a shared parent domain does not
rescue it either. Bearer tokens sidestep that entirely, at the cost of living
somewhere script can read them.

**gary-web's own log lines are in the browser console.** There is no server to
collect them. What survives is the `x-request-id` on each call, which gary-api
records too — so a line copied out of a console still finds its other half.
