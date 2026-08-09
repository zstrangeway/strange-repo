# strange-repo

A pnpm monorepo.

| App                              | Stack               | Port |
| -------------------------------- | ------------------- | ---- |
| [`example-web`](apps/example-web) | Next.js, TypeScript | 3000 |
| [`example-api`](apps/example-api) | FastAPI, Python     | 8000 |

## Requirements

- Node.js >= 22 and [pnpm](https://pnpm.io) 10
- [uv](https://docs.astral.sh/uv/) (manages the Python toolchain for `example-api`)

## Getting started

```bash
pnpm bootstrap   # pnpm install, then uv sync for the Python app
pnpm dev     # example-web on :3000, example-api on :8000
```

## Commands

Both apps expose the same script names, so anything below works repo-wide or for a
single app via `pnpm --filter <app> <script>`.

| Command          | What it does                                     |
| ---------------- | ------------------------------------------------ |
| `pnpm bootstrap` | Install dependencies for every app               |
| `pnpm dev`       | Run the apps in watch mode                       |
| `pnpm build`     | Production build (Next.js build / Python wheel)  |
| `pnpm start`     | Run the production builds                        |
| `pnpm test`      | Run the Cucumber/Gherkin suites                  |
| `pnpm lint`      | ESLint / Ruff                                    |
| `pnpm format`    | Prettier / Ruff format                           |
| `pnpm typecheck` | tsc / mypy                                       |
| `pnpm clean`     | Remove build output and caches                   |

## Testing

Development is test-first, and tests are written as Gherkin features — see
[CLAUDE.md](CLAUDE.md).

```
apps/example-web/features/          # .feature files
apps/example-web/features/steps/    # step definitions (TypeScript)
apps/example-api/tests/features/    # .feature files
apps/example-api/tests/step_defs/   # step definitions (pytest-bdd)
```

## Deployment

Both apps deploy to [Fly.io](https://fly.io) as containers. **Deploys run from
CI, not from a laptop** — merging to `main` is how you ship.

| Environment | Trigger | Apps |
| ----------- | ------- | ---- |
| Staging | Automatic on merge to `main` | `zs-example-web-staging`, `zs-example-api-staging` |
| Production | Manual approval on the `production` GitHub Environment | `zs-example-web`, `zs-example-api` |

Config lives in the repo, one file per app per environment:

```
apps/example-web/fly.toml            # production
apps/example-web/fly.staging.toml    # staging
apps/example-api/fly.toml
apps/example-api/fly.staging.toml
```

Staging machines stop when idle (`auto_stop_machines = "stop"`,
`min_machines_running = 0`), so an unused staging environment costs close to
nothing and the first request after a quiet period pays a cold start.
Production keeps one machine warm.

Every deploy is followed by [`scripts/smoke.sh`](scripts/smoke.sh), which checks
`/health` and one real route per app and fails the pipeline if either is wrong.

### One-time setup

```bash
brew install flyctl && fly auth login

# App names are globally unique across Fly — change the zs- prefix in the
# four fly.toml files if these are taken.
fly apps create zs-example-web
fly apps create zs-example-web-staging
fly apps create zs-example-api
fly apps create zs-example-api-staging

fly tokens create deploy       # add the result as the FLY_API_TOKEN repo secret
```

Then create a `production` GitHub Environment with a required reviewer — that
setting, not anything in the workflow file, is what gates production.

### Deploying by hand

Always from the repo root: the Dockerfiles need `pnpm-lock.yaml` and
`pnpm-workspace.yaml`, so the build context is the workspace, not the app
directory.

```bash
flyctl deploy . \
  --config apps/example-web/fly.staging.toml \
  --dockerfile apps/example-web/Dockerfile
```

### Runtime config

Secrets go through `fly secrets set`, never into `fly.toml`:

```bash
fly secrets set SOME_KEY=value --app zs-example-api-staging
```
