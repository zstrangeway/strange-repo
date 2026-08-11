import os

from behave import given, then, when


def _allow(context, origins):
    os.environ["BROWSER_ORIGINS"] = origins
    # The middleware reads its origins when the app is built, so the app has
    # to be rebuilt for a scenario to change them.
    context.rebuild_app()


@given('"{origin}" is allowed in a browser')
def step_allow_one(context, origin):
    _allow(context, origin)


@given('"{first}" and "{second}" are allowed in a browser')
def step_allow_two(context, first, second):
    _allow(context, f"{first},{second}")


def _preflight(context, origin, method):
    context.response = context.client.options(
        "/auth/sessions",
        headers={
            "origin": origin,
            "access-control-request-method": method,
            "access-control-request-headers": "authorization,content-type",
        },
    )


@when('a page at "{origin}" asks what it may send')
def step_preflight(context, origin):
    _preflight(context, origin, "GET")


@when('a page at "{origin}" asks whether it may sign someone in')
def step_preflight_post(context, origin):
    _preflight(context, origin, "POST")


@then('the answer should be addressed to "{origin}"')
def step_allowed(context, origin):
    allowed = context.response.headers.get("access-control-allow-origin")
    assert allowed == origin, f"addressed to {allowed!r}, expected {origin!r}"


@then("the answer should be addressed to nobody")
def step_not_allowed(context):
    allowed = context.response.headers.get("access-control-allow-origin")
    assert allowed is None, f"an unknown origin was welcomed: {allowed!r}"


@then("a session token should be allowed through")
def step_authorization_allowed(context):
    headers = context.response.headers.get("access-control-allow-headers", "")
    assert "authorization" in headers.lower(), (
        f"a browser could not send the token: {headers!r}"
    )


@then("POST should be allowed through")
def step_post_allowed(context):
    methods = context.response.headers.get("access-control-allow-methods", "")
    assert "POST" in methods.upper(), f"a browser could not sign in: {methods!r}"
