# gary-api

A FastAPI service.

## Run

```sh
uv run fastapi dev src/gary_api/app.py
```

## Test

Specs are Gherkin, run with behave. Coverage is gated at 100%.

```sh
uv run coverage run -m behave && uv run coverage report
```
