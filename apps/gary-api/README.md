# gary-api

A FastAPI service.

## Run

```sh
uv run fastapi dev src/gary_api/app.py   # development, with reload
uv run fastapi run src/gary_api/app.py   # production
```

## Test

Behavior is specified in Gherkin and run with behave; anything not reachable
through the API has a stdlib unittest alongside it. Coverage spans both runs and
is gated at 100%.

```sh
uv run coverage erase
uv run coverage run -m behave
uv run coverage run -a -m unittest discover -s tests
uv run coverage report
```
