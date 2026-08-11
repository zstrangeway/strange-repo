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

**Nothing sends mail today.** Password reset was the only thing that did, and
it left with the passwords. The layer is kept because the first feature that
needs to tell someone something will want it, and because deleting and
rewriting it costs more than leaving it — but no code path reaches it, so none
of the settings below currently do anything.

With nothing set, the console provider logs the message rather than sending it,
so a developer with no credentials sees it in full. A misconfigured provider is
logged at startup as an error but does **not** stop gary booting: taking the
service down over mail would fail Fly's health check and block the deploy that
fixes it.

HTTP rather than SMTP because Fly blocks outbound port 25 and 587 is unreliable
there — an SMTP provider works locally and then silently times out in
production.

The default sender needs no DNS but **only delivers to the address that owns the
Resend account**.

> **TODO: verify a sending domain and set `MAIL_FROM` before anything here
> sends to a real person.** The default sender accepts every message and
> quietly drops it for anyone but the Resend account owner, so the failure
> is invisible from gary's side. Nothing sends mail today, which is the
> only reason this is not already a problem.
>
> ```sh
> flyctl secrets set MAIL_FROM='gary <no-reply@your-domain>' -a gary-api
> ```
>
> Fine while gary is one person's, which is why it is a TODO and not a
> blocker.

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
