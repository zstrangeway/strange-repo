import json

from behave import then, when


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
