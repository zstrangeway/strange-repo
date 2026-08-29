"""Logging where an application got to."""

import re

from behave import given, then, use_step_matcher, when
from support.cli import run

from scout.applications import PATH

TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _history(context):
    """The history block of `scout show`, as a list of lines."""
    run(context, "show", context.ref)
    block = context.stdout.split("History", 1)[1].split("Posting", 1)[0]
    return [line.strip() for line in block.splitlines() if line.strip()]


# The regex matcher for these two only: behave's default `{status}` is greedy,
# so `as "screening" noting "..."` matches the shorter pattern too and the two
# steps are ambiguous. Switched back below, so the rest of the file reads
# normally.
use_step_matcher("re")


@when(r'I log that posting as "(?P<status>[^"]+)"')
@given(r'I log that posting as "(?P<status>[^"]+)"')
def step_log(context, status):
    run(context, "log", context.ref, status)


@when(r'I log that posting as "(?P<status>[^"]+)" noting "(?P<note>[^"]+)"')
def step_log_noting(context, status, note):
    run(context, "log", context.ref, status, "--note", note)


use_step_matcher("parse")


@given('I have logged that posting as "{status}"')
def step_have_logged(context, status):
    """Get the application to ``status``, however many steps that takes.

    A Given arranges state. Logging one status straight from `saved` would be
    asserting that the path is not enforced, which is a different scenario and
    one that exists a few lines further down.
    """
    for step in _walk_to(status):
        run(context, "log", context.ref, step)
        assert context.exit_code == 0, context.output


def _walk_to(status):
    if status in PATH:
        return PATH[1 : PATH.index(status) + 1]
    # An ending is reachable from anywhere, but a posting nobody ever applied
    # to being rejected is not the situation any of these scenarios mean.
    return ["applied", status]


@when('I log a posting that does not exist as "{status}"')
def step_log_missing(context, status):
    run(context, "log", "no-such-posting", status)


@when('I add the note "{note}"')
def step_add_note(context, note):
    run(context, "note", context.ref, note)


@then('its status should be "{status}"')
@then('its status should still be "{status}"')
def step_status(context, status):
    run(context, "show", context.ref)
    assert f"status   {status}" in context.stdout, context.stdout


@then('that posting\'s status should be "{status}"')
def step_that_status(context, status):
    step_status(context, status)


@then("its history should be one entry saying it was saved")
def step_history_one(context):
    lines = _history(context)
    assert len(lines) == 1, lines
    assert "saved" in lines[0], lines


@then('its history should end with "{status}"')
def step_history_ends(context, status):
    assert status in _history(context)[-1], _history(context)


@then("its history should end with that note")
def step_history_ends_note(context):
    assert "note" in _history(context)[-1], _history(context)


@then("its history should be {statuses}")
def step_history_is(context, statuses):
    wanted = [part.strip().strip('"') for part in statuses.split(",")]
    lines = _history(context)
    assert len(lines) == len(wanted), f"{wanted} against {lines}"
    for status, line in zip(wanted, lines, strict=True):
        assert status in line, f"{status} not in {line}"


@then("its history should still show it was ghosted")
def step_history_ghosted(context):
    assert any("ghosted" in line for line in _history(context))


@then("that entry should be stamped with when it happened")
def step_stamped(context):
    assert TIMESTAMP.search(_history(context)[-1]), _history(context)


@then('that entry\'s note should be "{note}"')
def step_entry_note(context, note):
    assert note in _history(context)[-1], _history(context)


@then('scout should say what I can log from "{status}"')
def step_says_allowed(context, status):
    assert f'From "{status}" you can log' in context.output, context.output


@then("scout should list the statuses there are")
def step_lists_statuses(context):
    assert "The statuses are" in context.output, context.output


@then("each one should show its status")
def step_each_status(context):
    for line in [x for x in context.stdout.splitlines() if x.strip()]:
        assert any(
            status in line
            for status in (
                "saved",
                "applied",
                "screening",
                "interview",
                "offer",
                "rejected",
                "ghosted",
            )
        ), line


@then("each one should show when it last moved")
def step_each_moved(context):
    for line in [x for x in context.stdout.splitlines() if x.strip()]:
        assert DATE.search(line), line
