# gary-api

A FastAPI service.

## Run

```sh
uv run fastapi dev src/gary_api/app.py   # development, with reload
uv run fastapi run src/gary_api/app.py   # production
```

## Test

Specs are Gherkin, run with behave. Coverage is gated at 100%.

```sh
uv run coverage run -m behave && uv run coverage report
```
