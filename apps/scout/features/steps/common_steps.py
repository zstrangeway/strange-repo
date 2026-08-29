"""Steps every feature leans on: the directory, the master resume, a posting."""

import os
import re

from behave import given, then, when
from support.cli import run, write_master

TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


@given("a scratch scout directory")
def step_scratch(context):
    """Already made by `before_scenario`; named so the specs can say so."""
    assert context.home.exists()


@given('a master resume naming "{first}" and "{second}"')
def step_master(context, first, second):
    write_master(context, first=first, second=second)


@given('the master resume claiming "{one}", "{two}" and "{three}"')
def step_master_skills(context, one, two, three):
    write_master(
        context,
        first=context.employers[0],
        second=context.employers[1],
        skills=f"{one}, {two}, {three}",
    )


@given("there is no master resume")
def step_no_master(context):
    (context.home / "resumes" / "master.md").unlink(missing_ok=True)


@given("the master resume is empty")
def step_empty_master(context):
    (context.home / "resumes" / "master.md").write_text("   \n", encoding="utf-8")


@given("the master resume says I led a team of 3")
def step_master_team(context):
    assert "Led a team of 3" in context.master


@given("no OpenRouter API key is set")
def step_no_key(context):
    os.environ.pop("OPENROUTER_API_KEY", None)
    # The fake provider has no key to be missing, so this is the one scenario
    # that drives the real one. It refuses before opening a connection.
    context.provider = "openrouter"


@given('I have saved a posting for "{title}" at "{company}"')
@when('I have saved a posting for "{title}" at "{company}"')
def step_saved_posting(context, title, company):
    body = (
        f"{title} at {company}. We are looking for somebody to own the "
        "platform, working in Python against Postgres, with Terraform "
        "describing the infrastructure underneath it. Kubernetes experience "
        "is a plus."
    )
    context.posting_body = body
    run(context, "save", "--text", body, "--title", title, "--company", company)
    assert context.exit_code == 0, context.output
    context.ref = context.stdout.splitlines()[0].removeprefix("Saved ").strip()


@then("scout should refuse it")
def step_refused(context):
    assert context.exit_code == 1, f"expected a refusal, got:\n{context.output}"


@then("scout should say no such posting")
def step_no_such_posting(context):
    assert "no posting called" in context.output, context.output
