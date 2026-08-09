# gary-api

A FastAPI service.

## Run

```sh
task gary-api:dev     # development, with reload
task gary-api:serve   # production
```

## Test

Behavior is specified in Gherkin and run with behave; anything not reachable
through the API has a stdlib unittest alongside it. Coverage spans both runs and
is gated at 100%.

```sh
task gary-api:test
```
