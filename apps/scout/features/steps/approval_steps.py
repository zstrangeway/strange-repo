"""Approving what is about to be sent."""

from behave import given, then, when
from support.cli import run

ANSWER = (
    "Because the work is the part of platform engineering I have kept "
    "choosing, and the posting describes it the way I would."
)


def _package(context):
    run(context, "package", context.ref)
    return context.output


@when("I assemble a package for that posting")
@given("I have assembled a package for that posting")
def step_assemble(context):
    run(context, "package", context.ref)


@when("I read that package")
def step_read(context):
    _package(context)


@then("the package should include the tailored resume at version {version:d}")
def step_includes_resume(context, version):
    assert f"Resume, version {version}" in context.output, context.output


@then("the package should say what changed in that resume")
def step_says_what_changed(context):
    assert "moved up" in context.output or "rewritten" in context.output, context.output


@when('I add the answer "{question}" to that package')
@given('I add the answer "{question}" to that package')
def step_add_answer(context, question):
    run(context, "answer", context.ref, question, ANSWER)
    context.answered = question


@given("I have added an answer to that package")
def step_have_added_answer(context):
    step_add_answer(context, "Why do you want to work here?")


@when('I add the answer "{question}" with nothing in it')
def step_add_empty_answer(context, question):
    run(context, "answer", context.ref, question, "   ")


@then("the package should include that answer in full")
def step_includes_answer(context):
    _package(context)
    assert ANSWER in context.output, context.output


@then("the package should include the tailored resume as well")
def step_includes_resume_too(context):
    assert "Resume, version" in context.output, context.output


@then("the resume should be marked as checked against the master resume")
def step_resume_checked(context):
    line = next(
        line for line in context.output.splitlines() if line.startswith("--- Resume")
    )
    assert "[checked]" in line, line


@then("the answer should be marked as scanned rather than checked")
def step_answer_scanned(context):
    line = next(
        line
        for line in context.output.splitlines()
        if line.startswith("--- ") and "Resume" not in line
    )
    assert "scanned" in line, line
    assert "[checked]" not in line, line


@then("the package should say in words that not everything in it was checked")
def step_says_not_everything(context):
    assert "NOT everything in this package was checked" in context.output, (
        context.output
    )


@then("the package should say what the check does not cover")
def step_says_what_is_not_covered(context):
    assert "Answers are SCANNED, not checked" in context.output, context.output


# ------------------------------------------------------------------ scanning


@when('I add an answer claiming "{term}", which the posting asks for')
def step_answer_claiming(context, term):
    assert term.lower() in context.posting_body.lower(), (
        f"{term} is not in the posting this scenario claims it is in"
    )
    run(
        context,
        "answer",
        context.ref,
        "Why do you want to work here?",
        f"I have deep experience with {term} and would bring it here.",
    )
    context.answered = "Why do you want to work here?"


@when('I add an answer mentioning "{term}", which nobody asked for')
def step_answer_mentioning(context, term):
    assert term.lower() not in context.posting_body.lower(), (
        f"{term} is in the posting, so this scenario is not testing what it says"
    )
    run(
        context,
        "answer",
        context.ref,
        "Anything else?",
        f"I once wrote a great deal of {term} and remember it fondly.",
    )
    context.answered = "Anything else?"


@when('I add an answer mentioning only "{one}" and "{two}"')
def step_answer_from_master(context, one, two):
    run(
        context,
        "answer",
        context.ref,
        "Why do you want to work here?",
        f"The work I keep choosing is {one} and {two}, which is what this is.",
    )
    context.answered = "Why do you want to work here?"


@then("the answer should be flagged for {count:d} thing to check")
def step_flagged(context, count):
    _package(context)
    line = next(
        line
        for line in context.output.splitlines()
        if line.startswith("--- ") and "Resume" not in line
    )
    assert f"scanned, {count} to check" in line, line


@then("the answer should have nothing flagged")
def step_nothing_flagged(context):
    _package(context)
    line = next(
        line
        for line in context.output.splitlines()
        if line.startswith("--- ") and "Resume" not in line
    )
    assert "nothing flagged" in line, line


@then('the package should say the posting asks for "{term}"')
def step_says_posting_asks(context, term):
    _package(context)
    assert f'"{term}" — the posting asks for this' in context.output, context.output


@then('the package should not say the posting asks for "{term}"')
def step_says_posting_does_not_ask(context, term):
    _package(context)
    assert f'"{term}" — the posting asks for this' not in context.output, context.output
    assert f'"{term}" — not in your master resume' in context.output, context.output


@then("the package should say the master resume does not mention it")
def step_says_master_lacks_it(context):
    assert "your master resume does not mention it" in context.output, context.output


@then("the answer should still be in the package")
def step_answer_still_there(context):
    _package(context)
    assert context.answered in context.output, context.output


@then("scout should not have refused it")
def step_not_refused(context):
    assert context.exit_code == 0, context.output


@then("the package should say answers are scanned rather than checked")
def step_says_scanned(context):
    assert "Answers are SCANNED, not checked" in context.output, context.output


@then("the package should say what the scan can and cannot find")
def step_says_scan_limits(context):
    assert "The scan finds names" in context.output, context.output
    assert "cannot tell" in context.output, context.output


@then("the package should say the whole of it was checked")
def step_says_all_checked(context):
    assert "Everything in this package was checked" in context.output, context.output
    assert "NOT everything" not in context.output, context.output


@when("I assemble a package for that posting again")
def step_assemble_again(context):
    run(context, "package", context.ref)


@then("scout should say there is no tailored resume for that posting yet")
def step_no_resume(context):
    assert "no tailored resume" in context.output, context.output


# ----------------------------------------------------------------- approving


@when("I approve that package")
def step_approve(context):
    run(context, "approve", context.ref)


@given("I have approved a package for that posting")
def step_have_approved(context):
    run(context, "package", context.ref)
    assert context.exit_code == 0, context.output
    run(context, "approve", context.ref)
    assert context.exit_code == 0, context.output


@then("the package should be approved")
def step_is_approved(context):
    _package(context)
    assert "Approved 2" in context.output, context.output
    assert "NOT approved" not in context.output, context.output


@then("its history should show when it was approved")
def step_approval_stamped(context):
    _package(context)
    assert "Approved 20" in context.output, context.output


@then("that package should no longer be approved")
def step_not_approved(context):
    _package(context)
    assert "NOT approved" in context.output, context.output


@then("scout should say the resume changed after it was approved")
def step_says_resume_changed(context):
    assert "Resume, version" in context.output, context.output
    assert "changed" in context.output, context.output


@then("scout should say what changed after it was approved")
def step_says_what_changed_after(context):
    assert context.answered in context.output, context.output


@when("I change an answer in that package")
@given("I have changed an answer in that package")
def step_change_answer(context):
    run(context, "answer", context.ref, context.answered, "Something else entirely.")


@when("I approve a package for a posting that does not exist")
def step_approve_missing(context):
    run(context, "approve", "no-such-posting")


# ---------------------------------------------------------------- afterwards


@then("it should show the resume exactly as it was approved")
def step_shows_approved_resume(context):
    assert "Resume, version" in context.output, context.output
    assert "Wilding Labs" in context.output, context.output


@then("it should show every answer exactly as it was approved")
def step_shows_approved_answers(context):
    assert ANSWER in context.output, context.output


@then("that posting should still show the package I approved")
def step_still_shows_package(context):
    _package(context)
    assert "Approved 2" in context.output, context.output
