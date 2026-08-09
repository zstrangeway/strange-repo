from starlette.testclient import TestClient

from gary_api.app import app


def before_scenario(context, scenario):
    context.client = TestClient(app)
    context.response = None


def after_scenario(context, scenario):
    context.client.close()
