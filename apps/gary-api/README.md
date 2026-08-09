# gary-api

A FastAPI service backed by Postgres. `GET /health` reports its own state and
the database's, always at 200 — the app answering is the signal that it is up,
and the body carries what it depends on.

## Database

Set `DATABASE_URL`; it defaults to `postgresql://postgres@127.0.0.1:5432/postgres`.
A `postgres://` or `postgresql://` URL is upgraded to the async driver
automatically, so a provider's connection string works unmodified.

```sh
pnpm exec task gary-api:migrate                       # apply migrations
pnpm exec task gary-api:revision -- "add widgets"     # generate one
```

Deploys run `alembic upgrade head` as Fly's `release_command`, before the new
version takes traffic.

## Run

```sh
pnpm install     # once, from the repo root
pnpm dev         # development, with reload
pnpm serve       # production
```

## Test

Behavior is specified in Gherkin and run with behave; anything not reachable
through the API has a stdlib unittest alongside it. Coverage spans both runs and
is gated at 100%.

```sh
pnpm test
```
