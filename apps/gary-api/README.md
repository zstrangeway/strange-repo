# gary-api

A FastAPI service backed by Postgres. It owns accounts, sessions and password
reset; gary-web calls it from its own server and never from a browser.

Passwords are argon2id. Session and reset tokens are random and stored only as
SHA-256 digests, so a copy of the database is not enough to impersonate anyone.
Sign-in answers identically for a wrong password and an unknown address, and
password reset answers identically whether or not the address is known —
either difference would turn the endpoint into a way to ask who has an account.

`GET /health` reports its own state and the database's, always at 200 — the app
answering is the signal that it is up, and the body carries what it depends on.
It exists for Fly's health check, which is what `fly.toml` calls.

## Database

Set `DATABASE_URL`; it defaults to `postgresql://postgres@127.0.0.1:5432/postgres`.
A `postgres://` or `postgresql://` URL is upgraded to the async driver
automatically, so a provider's connection string works unmodified.

```sh
pnpm exec task gary-api:migrate                       # apply migrations
pnpm exec task gary-api:revision -- "add widgets"     # generate one
```

```sh
pnpm exec task gary-api:seed                          # local accounts
```

`seed` migrates, then creates or resets `ada@`, `alan@` and `grace@example.com`
— all with the password it prints. Re-running is safe and puts a mangled local
database back rather than failing on the duplicate email. It refuses to run
unless `DATABASE_URL` looks local, because those accounts have a published
password.

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

Locally, set them in the environment for the command that needs them —
`RESEND_API_KEY=re_… pnpm dev`. There is deliberately no `.env` loading: go-task
refuses `dotenv` in an included Taskfile, so it would work when run from the
repo root and silently not when run per app, which is worse than not having it.

In production these are Fly **secrets**, not `[env]` in `fly.toml` — that file
is committed:

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
