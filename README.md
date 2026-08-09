# strange-repo

A pnpm + uv monorepo.

| App | Stack | What it is |
| --- | --- | --- |
| [`apps/gary-api`](apps/gary-api) | FastAPI | Serves `GET /health` |
| [`apps/gary-web`](apps/gary-web) | Next.js | Displays gary-api's health |

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

Fly app names are globally unique, so `gary-api` and `gary-web` may already be
taken. Pick names, then keep three places in sync: `app` in each `fly.toml`, and
`GARY_API_URL` in `apps/gary-web/fly.toml`, which resolves gary-api over Fly's
private network as `http://<gary-api-app-name>.internal:8080`.

```sh
flyctl apps create <gary-api-app-name>
flyctl apps create <gary-web-app-name>
```

Then add a deploy token to the repository as the `FLY_API_TOKEN` secret:

```sh
flyctl tokens create deploy --name github-actions
```

### How the two apps find each other

gary-web fetches gary-api over `.internal`, which stays inside the Fly org and
never traverses the public internet. That address routes straight to the
machine rather than through Fly's proxy, so it cannot wake a stopped one —
which is why gary-api sets `min_machines_running = 1`. To let gary-api scale to
zero instead, allocate a private address and switch `GARY_API_URL` to
`http://<gary-api-app-name>.flycast:8080`.

When gary-api is unreachable, gary-web renders `unavailable` rather than
failing, so a gary-api outage degrades the page instead of breaking it.
