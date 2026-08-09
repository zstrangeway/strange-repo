# strange-repo

A pnpm + uv monorepo.

| App | Stack | What it is |
| --- | --- | --- |
| [`apps/gary-api`](apps/gary-api) | FastAPI + Postgres | Accounts, sessions and password reset |
| [`apps/gary-web`](apps/gary-web) | Next.js | Signs you in and welcomes you home |

## Working on it

```sh
pnpm install     # once, from this directory
pnpm test        # every app's specs
```

Per-app commands live in each app's `Taskfile.yml` and are reachable as
`pnpm --filter <app> <script>`, or `pnpm exec task --list` to see them all.

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
`GARY_API_URL` in `apps/gary-web/fly.toml` too, since that embeds the API's app
name as `http://<gary-api-app-name>.internal:8080`.

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

Nothing in the browser talks to gary-api. gary-web calls it from its own
server, and the browser only ever talks to gary-web.

That is not a preference, it is what makes sessions work. gary-web and gary-api
are different sites, so a cookie set by gary-api would be third-party to
gary-web — blocked outright by Safari and Firefox, partitioned by Chrome. A
shared parent domain does not rescue it either, because `fly.dev` is on the
public suffix list. So gary-web owns the session cookie on its own origin and
holds the gary-api token inside it.

Two things follow. gary-api needs no CORS, because there is no cross-origin
browser request left to allow. And `GARY_API_URL` could now be a Fly-private
address, since only a server resolves it — it is left public because this repo
has been round the houses with Flycast already.

**These calls do not appear in browser devtools.** You will see gary-web's own
request and nothing else; the gary-api call is in the gary-web server log.
Worth knowing before spending an hour in the network tab.

`GARY_API_URL` is read per request rather than being a `NEXT_PUBLIC_` variable
— those are inlined at build time, which would bake the value into the image.

gary-api emails password reset links, so it needs `WEB_BASE_URL` pointing at
gary-web. That one is opened by a person, so it must be the public URL.
