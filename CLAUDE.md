# strange-repo

pnpm monorepo. Apps live in `apps/*`.

| App           | Stack                        | Port |
| ------------- | ---------------------------- | ---- |
| `example-web` | Next.js, TypeScript          | 3000 |
| `example-api` | FastAPI, Python (managed by `uv`) | 8000 |

## Commands

Every app exposes the same script names. Run them for the whole repo, or for one app
with `--filter`:

```bash
pnpm bootstrap  # install everything (pnpm workspaces + uv sync)
pnpm dev        # run all apps
pnpm test       # run all BDD suites
pnpm lint
pnpm format
pnpm typecheck
pnpm build
pnpm clean

pnpm --filter example-api test
```

Prefer these over calling `next`, `uv`, `pytest`, or `cucumber-js` directly.

Do not add a script named `setup` or `deploy` — both are pnpm builtins and would
shadow the script silently.

## Testing: TDD with Cucumber/Gherkin

**Write the `.feature` file first.** Every change starts with a failing scenario, then the
step definitions, then the implementation. Red, green, refactor — do not write production
code before there is a scenario that fails without it.

Scenarios describe behavior in the language of the domain, not the implementation. Say
"the visitor is greeted by name", not "greet() returns a string".

- `example-web` — `@cucumber/cucumber`. Features in `features/`, steps in `features/steps/`.
- `example-api` — `pytest-bdd`. Features in `tests/features/`, steps in `tests/step_defs/`.

Both apps' greeting feature is the working reference for the pattern.

## Deployment

Both apps ship to Fly.io as containers. **Deploys happen in CI, never from a
laptop** — merge to `main` for staging, approve the `production` GitHub
Environment for production. See the Deployment section of [README.md](README.md).

Anything that must run before an app serves traffic belongs in its `Dockerfile`;
anything environment-specific belongs in `fly.toml` / `fly.staging.toml` or in
`fly secrets`, never committed.
