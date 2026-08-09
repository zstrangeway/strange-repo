import json
import re
from datetime import datetime, timedelta, timezone

from behave import given, then, when

from environment import sql
from gary_api.passwords import verify_password

PASSWORD = "a long enough password"


def _headers(context):
    if context.token:
        return {"authorization": f"Bearer {context.token}"}
    return {}


def _register(context, email, password, display_name="Ada"):
    return context.client.post(
        "/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )


def _sign_in(context, email, password):
    return context.client.post(
        "/auth/sessions", json={"email": email, "password": password}
    )


def _reset_link(context):
    """The token out of the body gary actually posted to the provider."""
    assert context.mail.sent, "no email was sent"
    text = context.mail.sent[-1]["text"]
    found = re.search(r"[?&]token=([\w\-]+)", text)
    assert found, f"no reset link in: {text}"
    return found.group(1)


@given('a user exists with email "{email}" and password "{password}"')
def step_user_exists(context, email, password):
    response = _register(context, email, password)
    assert response.status_code == 201, response.text
    # Arranging a user should not leave the scenario signed in as them.
    context.token = None


@given('the user "{email}" has display name "{name}"')
def step_user_has_display_name(context, email, name):
    sql("UPDATE users SET display_name = :name WHERE email = :email",
        name=name, email=email.lower())


@given('no user exists with email "{email}"')
@then('no user should exist with email "{email}"')
def step_no_user(context, email):
    rows = sql("SELECT 1 FROM users WHERE email = :email", email=email.lower())
    assert not rows, f"{email} exists"


@given('I am signed in as "{email}" with password "{password}"')
def step_signed_in(context, email, password):
    response = _sign_in(context, email, password)
    assert response.status_code == 201, response.text
    context.token = response.json()["token"]


@given("I am also signed in on another device")
def step_signed_in_elsewhere(context):
    rows = sql("SELECT email FROM users LIMIT 1")
    response = _sign_in(context, rows[0][0], PASSWORD)
    assert response.status_code == 201, response.text
    context.other_token = response.json()["token"]


@given("my session expired an hour ago")
def step_session_expired(context):
    sql("UPDATE sessions SET expires_at = :when",
        when=datetime.now(timezone.utc) - timedelta(hours=1))


@given("I carry a session token that was never issued")
def step_bogus_token(context):
    context.token = "not-a-token-anyone-ever-issued"


@given('"{email}" has asked for a reset link')
def step_asked_for_reset(context, email):
    response = context.client.post("/auth/password-reset", json={"email": email})
    assert response.status_code == 202, response.text
    context.reset_token = _reset_link(context)


@given("I keep that first token")
def step_keep_first_token(context):
    context.first_token = context.reset_token


@given('the emailed token has already been used to set the password "{password}"')
def step_token_already_used(context, password):
    response = context.client.post(
        "/auth/password-reset/confirm",
        json={"token": context.reset_token, "new_password": password},
    )
    assert response.status_code == 204, response.text


@given("the emailed token expired an hour ago")
def step_reset_token_expired(context):
    sql("UPDATE password_reset_tokens SET expires_at = :when",
        when=datetime.now(timezone.utc) - timedelta(hours=1))


@when('"{email}" asks for a reset link again')
def step_asks_again(context, email):
    response = context.client.post("/auth/password-reset", json={"email": email})
    assert response.status_code == 202, response.text


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


@when('I POST "{path}" with the emailed token and:')
def step_post_with_token(context, path):
    body = json.loads(context.text) | {"token": context.reset_token}
    context.response = context.client.post(path, json=body)


@when('I POST "{path}" with the first token and:')
def step_post_with_first_token(context, path):
    body = json.loads(context.text) | {"token": context.first_token}
    context.response = context.client.post(path, json=body)


@when('I POST "{path}" with a token that was never issued and:')
def step_post_with_bogus_token(context, path):
    body = json.loads(context.text) | {"token": "never-issued"}
    context.response = context.client.post(path, json=body)


@then('the response field "{field}" should be "{expected}"')
def step_field(context, field, expected):
    actual = context.response.json().get(field)
    assert actual == expected, f"expected {field} {expected!r}, got {actual!r}"


@then("the response should carry no password")
def step_no_password(context):
    body = context.response.text
    assert "password" not in body.lower(), f"password leaked in: {body}"


@then("I should be signed in")
def step_should_be_signed_in(context):
    token = context.token
    # Sign-in and register answer with a token; 204s like a password change
    # have no body to read one from, and leave the current session standing.
    if context.response is not None and context.response.content:
        token = context.response.json().get("token", token)

    assert token, "no session token"
    check = context.client.get("/auth/me", headers={"authorization": f"Bearer {token}"})
    assert check.status_code == 200, f"not signed in: {check.status_code}"
    context.token = token


@then("I should not be signed in")
def step_should_not_be_signed_in(context):
    if not context.token:
        return
    check = context.client.get(
        "/auth/me", headers={"authorization": f"Bearer {context.token}"}
    )
    assert check.status_code == 401, f"still signed in: {check.status_code}"


@then("the session on the other device should still work")
def step_other_session_works(context):
    check = context.client.get(
        "/auth/me", headers={"authorization": f"Bearer {context.other_token}"}
    )
    assert check.status_code == 200, f"other device signed out: {check.status_code}"


@then("the session on the other device should be refused")
def step_other_session_refused(context):
    check = context.client.get(
        "/auth/me", headers={"authorization": f"Bearer {context.other_token}"}
    )
    assert check.status_code == 401, f"other device still signed in: {check.status_code}"


@then('the user "{email}" should have display name "{name}"')
def step_user_display_name(context, email, name):
    rows = sql("SELECT display_name FROM users WHERE email = :email", email=email.lower())
    assert rows and rows[0][0] == name, f"got {rows}"


@then('the stored password for "{email}" should not be "{password}"')
def step_password_not_plain(context, email, password):
    rows = sql("SELECT password_hash FROM users WHERE email = :email", email=email.lower())
    assert rows[0][0] != password, "password stored in the clear"


@then('the stored password for "{email}" should verify "{password}"')
def step_password_verifies(context, email, password):
    rows = sql("SELECT password_hash FROM users WHERE email = :email", email=email.lower())
    assert verify_password(rows[0][0], password), "hash does not verify"


@then('the stored password for "{email}" should reject "{password}"')
def step_password_rejects(context, email, password):
    rows = sql("SELECT password_hash FROM users WHERE email = :email", email=email.lower())
    assert not verify_password(rows[0][0], password), "hash accepted a wrong password"


@then('"{email}" should be able to sign in with "{password}"')
def step_can_sign_in(context, email, password):
    response = _sign_in(context, email, password)
    assert response.status_code == 201, f"could not sign in: {response.text}"


@then('"{email}" should not be able to sign in with "{password}"')
def step_cannot_sign_in(context, email, password):
    response = _sign_in(context, email, password)
    assert response.status_code == 401, f"signed in unexpectedly: {response.status_code}"


@then('a password reset email should be sent to "{email}"')
def step_mail_sent(context, email):
    assert context.mail.sent, "no email was sent"
    recipients = context.mail.sent[-1]["to"]
    assert recipients == [email], f"sent to {recipients}"


@then("the email should carry a reset link")
def step_mail_has_link(context):
    assert _reset_link(context)


@then("no email should be sent")
def step_no_mail(context):
    assert not context.mail.sent, f"sent {len(context.mail.sent)} email(s)"


@when("I check the emailed token")
def step_check_token(context):
    context.response = context.client.get(
        f"/auth/password-reset/{context.reset_token}"
    )


@when("I check a token that was never issued")
def step_check_bogus_token(context):
    context.response = context.client.get("/auth/password-reset/never-issued")


@given("the mail provider refuses everything")
def step_mail_refuses(context):
    context.mail.refusing = True
