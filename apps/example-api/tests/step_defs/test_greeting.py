"""Step definitions for features/greeting.feature."""

from fastapi.testclient import TestClient
from pytest_bdd import parsers, scenarios, then, when

from tests.conftest import Context

scenarios("greeting.feature")


@when(parsers.parse('the client requests a greeting for "{name}"'))
def request_greeting_for(client: TestClient, context: Context, name: str) -> None:
    context.response = client.get("/greet", params={"name": name})


@when("the client requests a greeting with no name")
def request_greeting_without_name(client: TestClient, context: Context) -> None:
    context.response = client.get("/greet")


@then(parsers.parse('the greeting message is "{message}"'))
def greeting_message_is(context: Context, message: str) -> None:
    assert context.result.json()["message"] == message
