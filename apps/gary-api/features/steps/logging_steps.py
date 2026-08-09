import asyncio
import json
import os
import re

import httpx
from behave import given, then, when

from gary_api import logs, mail
from gary_api.app import app


def lines(context):
    """Every line the log has taken so far, parsed.

    Parsing is the assertion: a line that is not one JSON object fails here
    rather than somewhere downstream in a log shipper nobody is watching.
    """
    parsed = []
    for number, raw in enumerate(context.log.getvalue().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            parsed.append(json.loads(raw))
        except json.JSONDecodeError as error:
            raise AssertionError(f"line {number} is not JSON: {raw!r} ({error})")
    return parsed


def line_for(context, message):
    found = [line for line in lines(context) if line.get("message") == message]
    assert found, f"nothing logged for {message!r}. Log was:\n{context.log.getvalue()}"
    return found[-1]


def at(line, path):
    """Look up "error.type" style paths, so nesting is assertable."""
    value = line
    for part in path.split("."):
        assert isinstance(value, dict) and part in value, f"{path} missing from {line}"
        value = value[part]
    return value


def _boom(text):
    raise ValueError(text)


@given("mail is going to the console")
def step_console_mail(context):
    # The rest of the suite runs the real Resend provider against a local
    # server. This scenario is about what the console provider writes, which
    # is what a developer machine and the end-to-end run both use.
    os.environ["MAIL_PROVIDER"] = "console"
    mail.mailer.cache_clear()


@given('LOG_LEVEL is "{level}"')
def step_log_level(context, level):
    os.environ["LOG_LEVEL"] = level
    # Reconfigured rather than nudged: this is the same call the app makes at
    # startup, so the spec exercises the real path to the level being set.
    logs.configure(stream=context.log)


@when('something logs "{message}" at {level:w}')
def step_log_at(context, message, level):
    getattr(logs.get_logger("gary_api.specs"), level)(message)


@when('something logs "{message}" outside any request')
def step_log_outside(context, message):
    logs.get_logger("gary_api.specs").info(message)


@when('something logs "{message}" with provider "{provider}" and attempts {attempts:d}')
def step_log_fields(context, message, provider, attempts):
    logs.get_logger("gary_api.specs").info(message, provider=provider, attempts=attempts)


@when('something logs "{message}" with level "{level}"')
def step_log_reserved(context, message, level):
    logs.get_logger("gary_api.specs").info(message, level=level)


@when('something logs "{message}" with a field that JSON cannot serialise')
def step_log_unserialisable(context, message):
    logs.get_logger("gary_api.specs").info(message, cursor=object())


@when('something logs a failure with a ValueError saying "{text}"')
def step_log_failure(context, text):
    try:
        _boom(text)
    except ValueError:
        logs.get_logger("gary_api.specs").exception("work.failed")


@when('a library logger named "{name}" logs "{message}"')
def step_library_log(context, name, message):
    import logging

    logging.getLogger(name).info(message)


@when('I GET "{path}" carrying the request id {value}')
def step_get_with_request_id(context, path, value):
    context.response = context.client.get(path, headers={"x-request-id": value})


@when('I GET "{path}" twice at the same time')
def step_get_concurrently(context, path):
    async def both():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://spec") as client:
            # One event loop, both in flight together. Two clients on two
            # loops would isolate the context by accident and prove nothing.
            return await asyncio.gather(client.get(path), client.get(path))

    context.responses = asyncio.run(both())


@then("every logged line should be a single JSON object")
def step_all_json(context):
    parsed = lines(context)
    assert parsed, "nothing was logged at all"
    for line in parsed:
        assert isinstance(line, dict), f"expected an object, got {line!r}"


@then('every line should carry "timestamp", "level", "logger", "message" and "app"')
def step_all_carry_core(context):
    for line in lines(context):
        missing = {"timestamp", "level", "logger", "message", "app"} - set(line)
        assert not missing, f"{sorted(missing)} missing from {line}"


@then('every line should have "{field}" set to "{value}"')
def step_all_field(context, field, value):
    for line in lines(context):
        assert line.get(field) == value, f"expected {field}={value!r} in {line}"


@then('the line for "{message}" should be a single JSON object')
@then('the line for "{message}" should still be a single JSON object')
def step_line_is_object(context, message):
    assert isinstance(line_for(context, message), dict)


@then('the line for "{message}" should have "{field}" set to "{value}"')
def step_line_field(context, message, field, value):
    actual = at(line_for(context, message), field)
    assert actual == value, f"expected {field}={value!r}, got {actual!r}"


@then('the line for "{message}" should have "{field}" set to the number {value:d}')
def step_line_number(context, message, field, value):
    actual = at(line_for(context, message), field)
    assert actual == value, f"expected {field}={value}, got {actual!r}"
    assert isinstance(actual, int), f"{field} came out as {type(actual).__name__}, not a number"


@then('the line for "{message}" should have no "{field}"')
def step_line_missing(context, message, field):
    line = line_for(context, message)
    assert field not in line, f"{field} should not be there, but {line} has it"


@then('the line for "{message}" should have a "timestamp" in UTC ISO-8601 with milliseconds')
def step_timestamp_shape(context, message):
    stamp = line_for(context, message)["timestamp"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", stamp), (
        f"{stamp!r} is not ISO-8601 UTC with milliseconds"
    )


@then('the line for "{message}" should describe that field as text')
def step_unserialisable_field(context, message):
    value = line_for(context, message)["cursor"]
    assert isinstance(value, str), f"expected text, got {type(value).__name__}"
    assert "object" in value, f"{value!r} says nothing about what the value was"


@then('nothing should have been logged for "{message}"')
def step_nothing_logged(context, message):
    found = [line for line in lines(context) if line.get("message") == message]
    assert not found, f"expected no line for {message!r}, found {found}"


@then('that line should have "{field}" set to "{value}"')
def step_failure_field(context, field, value):
    actual = at(line_for(context, "work.failed"), field)
    assert actual == value, f"expected {field}={value!r}, got {actual!r}"


@then('that line should have an "error.stack" mentioning the raising function')
def step_failure_stack(context):
    stack = at(line_for(context, "work.failed"), "error.stack")
    assert "_boom" in stack, f"the stack does not mention where it came from:\n{stack}"


@then("that line should not be followed by a bare traceback")
def step_no_bare_traceback(context):
    # The stack belongs inside the object. Loose after it, every shipper in
    # the world reads it as a handful of unparseable lines.
    for line in lines(context):
        assert "message" in line, f"a line came out with no message: {line}"


@then('the response should carry an "x-request-id" header')
def step_response_has_id(context):
    assert context.response.headers.get("x-request-id"), (
        f"no x-request-id on the response. Headers: {dict(context.response.headers)}"
    )


@then('the response should carry an "x-request-id" header set to "{value}"')
def step_response_id_is(context, value):
    actual = context.response.headers.get("x-request-id")
    assert actual == value, f"expected x-request-id={value!r}, got {actual!r}"


@then('every line logged while handling that request should have that same "request_id"')
def step_lines_share_id(context):
    step_request_id_lines(context, context.response.headers["x-request-id"])


@then('every line logged while handling that request should have "request_id" set to "{value}"')
def step_request_id_lines(context, value):
    during = [line for line in lines(context) if "request_id" in line]
    assert during, "no line carried a request id at all"
    for line in during:
        assert line["request_id"] == value, f"expected {value!r} in {line}"


@then('the two responses should carry different "x-request-id" headers')
def step_two_ids(context):
    first, second = (r.headers.get("x-request-id") for r in context.responses)
    assert first and second, f"missing an id: {first!r}, {second!r}"
    assert first != second, f"both requests were given {first!r}"
    context.request_ids = (first, second)


@then("no logged line should carry both request ids")
def step_ids_not_mixed(context):
    first, second = context.request_ids
    for line in lines(context):
        rendered = json.dumps(line)
        assert not (first in rendered and second in rendered), (
            f"one line carries both ids, so the context leaked: {line}"
        )


@then('there should be one "http.request" line')
def step_one_summary(context):
    found = [line for line in lines(context) if line.get("message") == "http.request"]
    assert len(found) == 1, f"expected one http.request line, got {len(found)}"
    context.summary = found[0]


@then('it should have "{field}" set to "{value}"')
def step_summary_field(context, field, value):
    actual = context.summary.get(field)
    assert actual == value, f"expected {field}={value!r}, got {actual!r}"


@then('it should have "{field}" set to the number {value:d}')
def step_summary_number(context, field, value):
    actual = context.summary.get(field)
    assert actual == value, f"expected {field}={value}, got {actual!r}"


@then('it should have a "duration_ms" that is a number')
def step_summary_duration(context):
    actual = context.summary.get("duration_ms")
    assert isinstance(actual, (int, float)), f"duration_ms came out as {actual!r}"
    assert actual >= 0, f"a request cannot take {actual}ms"


@then("a logged line should contain a reset link with a readable token")
def step_reset_link_readable(context):
    # Exactly the pattern the end-to-end suite uses against this app's real
    # stdout. If JSON escaping ever puts the link out of its reach, this is
    # where it gets noticed rather than in a red e2e run.
    raw = context.log.getvalue()
    found = re.findall(r"[?&]token=([\w-]+)", raw)
    assert found, f"no reset link survived in:\n{raw}"
