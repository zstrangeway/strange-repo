import json
from datetime import datetime, timedelta, timezone

from behave import given, then, when

from environment import sql

REDIRECT_URI = "http://localhost:3000/signed-in"


def _headers(context):
    if context.token:
        return {"authorization": f"Bearer {context.token}"}
    return {}


def code_for(subject, email, display_name):
    """A code the fake provider will read as this person.

    Matches gary_api.identity.fake: subject|email|display name. Written out
    here rather than imported so a change to that format has to be made
    deliberately in both places, instead of the specs silently agreeing with
    whatever the implementation now does.
    """
    return f"{subject}|{email}|{display_name}"


def _sign_in(context, provider, subject, email, display_name):
    return context.client.post(
        "/auth/sessions",
        json={
            "provider": provider,
            "code": code_for(subject, email, display_name),
            "redirect_uri": REDIRECT_URI,
        },
    )


@given('an account exists at {provider} for "{email}" named "{name}"')
def step_account_exists(context, provider, email, name):
    subject = f"subject-of-{email}"
    response = _sign_in(context, provider, subject, email, name)
    assert response.status_code == 201, response.text
    context.identities[(provider, email)] = subject
    context.accounts[email] = response.json()


@given('I am signed in at {provider} as "{email}" named "{name}"')
@when('I sign in at {provider} as "{email}" named "{name}"')
def step_sign_in(context, provider, email, name):
    subject = context.identities.get((provider, email), f"subject-of-{email}")
    context.response = _sign_in(context, provider, subject, email, name)
    if context.response.status_code == 201:
        context.identities[(provider, email)] = subject
        context.token = context.response.json()["token"]
        context.accounts.setdefault(email, context.response.json())


@when('I sign in at {provider} with a code it will not accept')
def step_sign_in_refused(context, provider):
    context.response = context.client.post(
        "/auth/sessions",
        json={
            "provider": provider,
            "code": "not-an-identity",
            "redirect_uri": REDIRECT_URI,
        },
    )


@when('I POST "{path}" with:')
def step_post(context, path):
    context.response = context.client.post(
        path, json=json.loads(context.text), headers=_headers(context)
    )


@when('I PATCH "{path}" with:')
def step_patch(context, path):
    context.response = context.client.patch(
        path, json=json.loads(context.text), headers=_headers(context)
    )


@when('I DELETE "{path}"')
def step_delete(context, path):
    context.response = context.client.delete(path, headers=_headers(context))


@then('the response field "{field}" should be "{expected}"')
def step_field(context, field, expected):
    actual = context.response.json().get(field)
    assert actual == expected, f"expected {field} {expected!r}, got {actual!r}"


@given("I am signed out")
def step_signed_out(context):
    context.token = None


@given('I connect {provider} as "{email}" named "{name}"')
@when('I connect {provider} as "{email}" named "{name}"')
def step_connect(context, provider, email, name):
    subject = context.identities.get((provider, email), f"subject-of-{email}")
    context.response = context.client.post(
        "/auth/me/identities",
        json={
            "provider": provider,
            "code": code_for(subject, email, name),
            "redirect_uri": REDIRECT_URI,
        },
        headers=_headers(context),
    )
    if context.response.status_code == 201:
        context.identities[(provider, email)] = subject


@when("I disconnect {provider}")
def step_disconnect(context, provider):
    context.response = context.client.delete(
        f"/auth/me/identities/{provider}", headers=_headers(context)
    )


@when('I ask where to sign in')
def step_list_providers(context):
    context.response = context.client.get(
        "/auth/providers", params={"redirect_uri": REDIRECT_URI, "state": "abc"}
    )


@given("only {providers} is configured")
@given("only {providers} are configured")
def step_only_configured(context, providers):
    import os

    from gary_api import identity

    os.environ["IDENTITY_PROVIDERS"] = providers.replace(" and ", ",").replace(" ", "")
    identity.provider.cache_clear()


@then("I should be signed in")
def step_should_be_signed_in(context):
    assert context.response.status_code in (200, 201), context.response.text
    token = context.response.json()["token"]
    me = context.client.get("/auth/me", headers={"authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    context.token = token


@then("I should not be signed in")
def step_should_not_be_signed_in(context):
    if context.token:
        me = context.client.get("/auth/me", headers=_headers(context))
        assert me.status_code == 401, f"the session still works: {me.text}"
        return

    assert context.response.status_code >= 400, context.response.text


@then('the account should be the one for "{email}"')
def step_same_account(context, email):
    expected = context.accounts[email]["id"]
    assert context.response.json()["id"] == expected, (
        f"expected the account for {email}, got a different one"
    )


@then('the account should not be the one for "{email}"')
def step_different_account(context, email):
    expected = context.accounts[email]["id"]
    assert context.response.json()["id"] != expected, (
        f"expected a different account from {email}'s, got the same one"
    )


@then("{provider} should be connected")
def step_connected(context, provider):
    listed = context.client.get("/auth/me/identities", headers=_headers(context))
    assert listed.status_code == 200, listed.text
    names = [row["provider"] for row in listed.json()]
    assert provider in names, f"{provider} is not connected; {names} are"


@then("{provider} should not be connected")
def step_not_connected(context, provider):
    listed = context.client.get("/auth/me/identities", headers=_headers(context))
    assert listed.status_code == 200, listed.text
    names = [row["provider"] for row in listed.json()]
    assert provider not in names, f"{provider} is connected and should not be"


@then('the address held for {provider} should be "{email}"')
def step_identity_email(context, provider, email):
    listed = context.client.get("/auth/me/identities", headers=_headers(context))
    found = next(row for row in listed.json() if row["provider"] == provider)
    assert found["email"] == email, f"held {found['email']!r}, expected {email!r}"


@then('the offered ways to sign in should be {expected}')
def step_offered(context, expected):
    wanted = [name.strip() for name in expected.replace(" and ", ",").split(",")]
    got = [row["name"] for row in context.response.json()]
    assert got == wanted, f"offered {got}, expected {wanted}"


@then("every way to sign in should carry somewhere to go")
def step_urls_present(context):
    for row in context.response.json():
        assert row["authorization_url"].startswith("http"), row


@given("I am also signed in on another device")
def step_other_device(context):
    other = context.client.post(
        "/auth/sessions",
        json={
            "provider": "google",
            "code": code_for("subject-of-ada@example.com", "ada@example.com", "Ada"),
            "redirect_uri": REDIRECT_URI,
        },
    )
    assert other.status_code == 201, other.text
    context.other_token = other.json()["token"]


@then("the session on the other device should still work")
def step_other_still_works(context):
    me = context.client.get(
        "/auth/me", headers={"authorization": f"Bearer {context.other_token}"}
    )
    assert me.status_code == 200, me.text


@given("my session expired an hour ago")
def step_session_expired(context):
    sql(
        "UPDATE sessions SET expires_at = :when",
        when=datetime.now(timezone.utc) - timedelta(hours=1),
    )


@given("I carry a session token that was never issued")
def step_bogus_token(context):
    context.token = "not-a-token-anyone-issued"


@then('the user "{email}" should have display name "{name}"')
def step_display_name(context, email, name):
    rows = sql("SELECT display_name FROM users WHERE email = :email", email=email)
    assert rows, f"no user with email {email}"
    assert rows[0][0] == name, f"display name is {rows[0][0]!r}, expected {name!r}"


@then("the response should carry no token")
def step_no_token(context):
    assert "token" not in context.response.json(), context.response.text
