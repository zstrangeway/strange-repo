"""Saving a posting, from text and from a URL."""

from behave import given, then, when
from support.board import JobBoard
from support.cli import run

PASTED = (
    "Senior Platform Engineer at Wilding Labs\n"
    "We are looking for someone with deep Postgres and Python experience."
)


def _save_text(context, text, title=None, company=None):
    argv = ["save", "--text", text]
    if title:
        argv += ["--title", title]
    if company:
        argv += ["--company", company]
    run(context, *argv)
    # Kept apart from context.output, which the next step clobbers as soon as
    # it runs `show` to check what landed in the row.
    context.save_output = context.output
    if context.exit_code == 0:
        context.ref = context.stdout.splitlines()[0].removeprefix("Saved ").strip()


@when("I save a posting pasted as")
@when("I save a posting pasted as:")
def step_save_docstring(context):
    _save_text(context, context.text)


@when('I save a posting pasted as "{text}"')
def step_save_inline(context, text):
    _save_text(context, text)


@when('I save that pasted posting as "{title}" at "{company}"')
def step_save_named(context, title, company):
    _save_text(context, PASTED, title=title, company=company)


@when("I save that pasted posting with no title or company")
def step_save_unnamed(context):
    _save_text(context, PASTED)


@then("the posting should be saved")
def step_saved(context):
    assert context.exit_code == 0, context.output
    assert "Saved " in context.stdout, context.output


@then("scout should tell me the posting's reference")
def step_reference(context):
    assert context.ref, context.output


@then('the posting text should mention "{phrase}"')
def step_text_mentions(context, phrase):
    run(context, "show", context.ref)
    assert phrase in context.stdout, context.stdout


@then('the posting\'s title should be "{title}"')
def step_title(context, title):
    run(context, "show", context.ref)
    assert f"title    {title}" in context.stdout, context.stdout


@then('the posting\'s company should be "{company}"')
def step_company(context, company):
    run(context, "show", context.ref)
    assert f"company  {company}" in context.stdout, context.stdout


@then("the posting's company should be recorded as unknown")
def step_company_unknown(context):
    run(context, "show", context.ref)
    assert "company  unknown" in context.stdout, context.stdout


@then("scout should say the company is unknown and how to set it")
def step_company_hint(context):
    assert "Company unknown" in context.save_output, context.save_output
    assert "scout edit" in context.save_output, context.save_output


@then("scout should say the posting was empty")
def step_empty(context):
    assert "posting was empty" in context.output, context.output


# ------------------------------------------------------------------- boards


@given('a job board serving a posting for "{title}" at "{company}"')
def step_board(context, title, company):
    context.board = JobBoard("posting", title=title, company=company)


@given("a job board that serves an empty JavaScript shell")
def step_board_shell(context):
    context.board = JobBoard("shell")


@given("a job board serving its whole index of jobs")
def step_board_index(context):
    context.board = JobBoard("index")


@given("a job board that answers 403")
def step_board_403(context):
    context.board = JobBoard("refuses")


@given("a job board that never answers")
def step_board_silent(context):
    context.board = JobBoard("silent")


@when("I save a posting from that URL")
@when("I save a posting from that URL again")
def step_save_url(context):
    run(context, "save", "--url", context.board.url)
    if context.exit_code == 0:
        context.ref = context.stdout.splitlines()[0].removeprefix("Saved ").strip()


@given("I have saved a posting from that URL")
def step_already_saved_url(context):
    step_save_url(context)
    assert context.exit_code == 0, context.output


@then("the posting's source URL should be that URL")
def step_source_url(context):
    run(context, "show", context.ref)
    assert context.board.url in context.stdout, context.stdout


@then("the posting text should be the readable part of the page")
def step_readable(context):
    run(context, "show", context.ref)
    assert "deep Postgres and Python experience" in context.stdout, context.stdout


@then("the posting text should not contain the page's navigation")
def step_no_nav(context):
    run(context, "show", context.ref)
    assert "About Bilgewater Boards" not in context.stdout, context.stdout


@then("scout should say the page had no readable posting in it")
def step_no_posting(context):
    assert "no readable posting" in context.output, context.output


@then("scout should say it looks like a list of jobs")
def step_looks_like_index(context):
    assert "list of jobs" in context.output, context.output


@then("scout should tell me to open the posting itself")
def step_open_the_posting(context):
    assert "Open the posting itself" in context.output, context.output


@then("scout should say the board refused the fetch")
def step_board_refused(context):
    assert "board refused the fetch" in context.output, context.output


@then("scout should say the fetch timed out")
def step_timed_out(context):
    assert "timed out" in context.output, context.output


@then("scout should tell me to paste the text instead")
def step_paste_instead(context):
    assert "Paste the text instead" in context.output, context.output


@then("scout should name the posting I already have")
def step_names_existing(context):
    assert "already saved as" in context.output, context.output


# ------------------------------------------------------------------ reading


@when("I list my postings")
def step_list(context):
    run(context, "list")


@when("I list the postings still in play")
def step_list_in_play(context):
    run(context, "list", "--in-play")


@then('the postings should be "{first}", "{second}"')
def step_listed_order(context, first, second):
    lines = [line for line in context.stdout.splitlines() if line.strip()]
    assert first in lines[0], context.stdout
    assert second in lines[1], context.stdout


@then('"{title}" should be listed')
def step_listed(context, title):
    assert title in context.stdout, context.stdout


@then('"{title}" should not be listed')
def step_not_listed(context, title):
    assert title not in context.stdout, context.stdout


@when("I read that posting")
def step_read(context):
    run(context, "show", context.ref)


@then("the posting text should be the whole text as saved")
def step_whole_text(context):
    assert "own the platform" in context.stdout, context.stdout
