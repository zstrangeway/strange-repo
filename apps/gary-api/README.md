# gary-api

A FastAPI service.

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
