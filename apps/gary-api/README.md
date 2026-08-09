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
version takes traffic. That gates the deploy on reaching the database, so an
unset or wrong `DATABASE_URL` fails the deploy rather than starting a service
that cannot work.

## Mail

`gary_api.mail` picks one provider from the environment at startup and reports
which in the log. Callers only ever see `mail.send(Message(...))`, so swapping
providers is a config change — or, for a provider that has no module yet, one
class and one line in `PROVIDERS`.

| | |
| --- | --- |
| `MAIL_PROVIDER` | `console` (default) or `resend` |
| `RESEND_API_KEY` | required by `resend`, and selects it on its own |
| `MAIL_FROM` | sender address, defaults to Resend's shared test sender |

With nothing set, the console provider logs the message rather than sending it,
so a developer with no credentials still sees the reset link in full. A
misconfigured provider is logged at startup as an error but does **not** stop
gary booting: mail matters only for password reset, and taking the service down
over it would fail Fly's health check and block the deploy that fixes it.

HTTP rather than SMTP because Fly blocks outbound port 25 and 587 is unreliable
there — an SMTP provider works locally and then silently times out in
production.

The default sender needs no DNS but **only delivers to the address that owns the
Resend account**. Set `MAIL_FROM` to an address on a verified domain before
anyone else signs up.

Locally, copy `.env.example` to `.env`; it is gitignored and loaded by the
Taskfile. In production these are Fly secrets:

```sh
flyctl secrets set RESEND_API_KEY=re_xxxxxxxx -a gary-api
```

`pnpm test` pins `MAIL_PROVIDER=console`, so a real key in the environment can
never turn a spec run into email sent to real people.

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
