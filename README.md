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
pnpm setup   # pnpm install, then uv sync for the Python app
pnpm dev     # example-web on :3000, example-api on :8000
```

## Commands

Both apps expose the same script names, so anything below works repo-wide or for a
single app via `pnpm --filter <app> <script>`.

| Command          | What it does                                     |
| ---------------- | ------------------------------------------------ |
| `pnpm setup`     | Install dependencies for every app               |
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
