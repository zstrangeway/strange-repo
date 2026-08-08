"""Step definitions for features/health.feature."""

from fastapi.testclient import TestClient
from pytest_bdd import parsers, scenarios, then, when

from tests.conftest import Context

scenarios("health.feature")


@when("the client requests the health check")
def request_health(client: TestClient, context: Context) -> None:
    context.response = client.get("/health")


@then(parsers.parse('the reported status is "{status}"'))
def reported_status_is(context: Context, status: str) -> None:
    assert context.result.json()["status"] == status
