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
