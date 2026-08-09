import json

from behave import given, then, when
from sqlalchemy.ext.asyncio import create_async_engine

from gary_api import db


@given("the database is unreachable")
def step_database_unreachable(context):
    # Nothing listens on port 1. create_async_engine does not connect until
    # used, so swapping it here is enough.
    db.engine = create_async_engine(
        "postgresql+asyncpg://postgres@127.0.0.1:1/postgres"
    )


@when('I GET "{path}"')
def step_get(context, path):
    context.response = context.client.get(path)


@then("the response status should be {expected:d}")
def step_status(context, expected):
    actual = context.response.status_code
    assert actual == expected, f"expected status {expected}, got {actual}"


@then("the response body should be:")
def step_body(context):
    actual = context.response.json()
    expected = json.loads(context.text)
    assert actual == expected, f"expected body {expected}, got {actual}"
