"""Shared fixtures and step definitions for the BDD suite."""

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from pytest_bdd import given, parsers, then

from example_api.main import app


@dataclass
class Context:
    """Scratch space for passing state between the steps of a scenario."""

    response: Response | None = None

    @property
    def result(self) -> Response:
        assert self.response is not None, "no request has been made yet"
        return self.response


@pytest.fixture
def client() -> TestClient:
    """An HTTP client bound to the app under test."""
    return TestClient(app)


@pytest.fixture
def context() -> Context:
    return Context()


@given("the API is running")
def api_is_running(client: TestClient) -> TestClient:
    return client


@then(parsers.parse("the response status is {status:d}"))
def response_status_is(context: Context, status: int) -> None:
    assert context.result.status_code == status
