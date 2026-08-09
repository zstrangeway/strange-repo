from starlette.testclient import TestClient

from gary_api import db
from gary_api.app import app

# Scenarios may point the app at a dead database; keep the real one so the
# next scenario starts from a working connection.
_real_engine = db.engine


def before_scenario(context, scenario):
    db.engine = _real_engine
    context.client = TestClient(app)
    context.response = None


def after_scenario(context, scenario):
    context.client.close()
