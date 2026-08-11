# gary-api

A FastAPI service backed by Postgres. It owns accounts, the identities that
reach them, and sessions. It holds no passwords: Google, Facebook and Apple
authenticate people and gary trusts the result.

Clients are anything — gary-web is a browser app, and an iOS or Android one
would call the same endpoints the same way. Sessions are bearer tokens, never
cookies, which is what keeps that true. `BROWSER_ORIGINS` names the origins a
browser may call from; without it the browser makes the call and then refuses
to hand back the answer.

Session tokens are random and stored only as SHA-256 digests, so a copy of the
database is not enough to impersonate anyone. Two providers naming the same
address are two accounts, deliberately: gary cannot verify an address, so
treating a match as proof would be a way into someone else's account.

`GET /health` reports its own state and the database's, always at 200 — the app
answering is the signal that it is up, and the body carries what it depends on.
It exists for Fly's health check, which is what `fly.toml` calls.

## Database

Set `DATABASE_URL`; it defaults to `postgresql://postgres@127.0.0.1:5432/postgres`.
A `postgres://` or `postgresql://` URL is upgraded to the async driver
automatically, so a provider's connection string works unmodified.

```sh
pnpm --filter gary-api migrate                    # apply migrations
pnpm --filter gary-api revision "add widgets"     # generate one
```

```sh
pnpm --filter gary-api seed                       # local accounts
```

`seed` migrates, then creates or resets `ada@`, `alan@` and `grace@example.com`.
Re-running is safe and puts a mangled local database back rather than failing on
the duplicate email. It refuses to run unless `DATABASE_URL` looks local,
because those accounts are reachable with a published sign-in code.

Deploys run `alembic upgrade head` as Fly's `release_command`, before the new
version takes traffic. That gates the deploy on reaching the database, so an
unset or wrong `DATABASE_URL` fails the deploy rather than starting a service
that cannot work.

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
