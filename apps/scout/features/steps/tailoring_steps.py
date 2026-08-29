"""Tailoring, and the check that the draft invented nothing."""

from behave import given, then, when
from support.cli import run, set_draft, tailored


def _swap_experience(master: str) -> str:
    """The two employer blocks, the other way round.

    A legal tailoring: nothing added, one section up and one down — which is
    what "reorder and reweight" means when the sections are jobs.
    """
    head, _, rest = master.partition("## Experience\n")
    blocks = rest.split("### ")
    first, second = blocks[1], blocks[2]
    return head + "## Experience\n" + "### " + second.rstrip() + "\n\n### " + first


@given("the model will return a draft drawn only from the master")
def step_draft_legal(context):
    set_draft(context, _swap_experience(context.master))


@given("the model will return a different draft drawn only from the master")
def step_draft_legal_different(context):
    draft = _swap_experience(context.master)
    set_draft(context, draft.replace("- Ran the release process every week\n", ""))


@given('the model will return a draft naming "{employer}" as an employer')
def step_draft_employer(context, employer):
    set_draft(
        context,
        context.master + f"\n### {employer} — Senior Engineer\n\n2015–2018\n\n"
        "- Ran the release process every week\n",
    )


@given('the model will return a draft claiming "{skill}"')
def step_draft_skill(context, skill):
    set_draft(
        context,
        context.master.replace(
            "Python, Postgres, Terraform", f"Python, Postgres, Terraform, {skill}"
        ),
    )


@given('the model will return a draft leading with "{first}" and "{second}"')
def step_draft_reordered_skills(context, first, second):
    set_draft(
        context,
        context.master.replace(
            "Python, Postgres, Terraform", f"{first}, {second}, Python"
        ),
    )


@given("the model will return a draft rephrasing my Wilding Labs work")
def step_draft_rephrased(context):
    set_draft(
        context,
        context.master.replace(
            "- Cut deploy time from 40 minutes to 4, on Postgres and Terraform",
            "- Deploy time cut from 40 minutes to 4, on Terraform and Postgres",
        ),
    )


@given('the model will return a draft ending a sentence with "{word}"')
def step_draft_punctuated(context, word):
    set_draft(
        context,
        context.master.replace(
            "- Ran the release process every week",
            f"- Ran the release process every week on {word}",
        ),
    )


@given("the model will return a draft saying I led a team of 12")
def step_draft_inflated(context):
    set_draft(context, context.master.replace("Led a team of 3", "Led a team of 12"))


@given('the model will return a draft moving "{first}" dates onto "{second}"')
def step_draft_moved_dates(context, first, second):
    del first  # named in the spec for what it reads like, not for a lookup
    set_draft(
        context,
        context.master.replace(
            f"### {second} — Platform Engineer\n\n2018–2021",
            f"### {second} — Platform Engineer\n\n2021–2025",
        ),
    )


@given("the model will fail")
def step_model_fails(context):
    directory = context.home / ".scout"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "fake-failure.txt").write_text("the provider returned 529")


@when("I tailor my resume for that posting")
def step_tailor(context):
    run(context, "tailor", context.ref, "--provider", context.provider)


@given("I have already tailored my resume for that posting")
def step_already_tailored(context):
    set_draft(context, _swap_experience(context.master))
    run(context, "tailor", context.ref, "--provider", "fake")
    assert context.exit_code == 0, context.output
    context.version_one = tailored(context, context.ref, 1).read_text(encoding="utf-8")


@given("I have tailored my resume for that posting")
def step_have_tailored(context):
    set_draft(context, _swap_experience(context.master))
    run(context, "tailor", context.ref, "--provider", context.provider)
    assert context.exit_code == 0, context.output


@when("I tailor my resume for that posting again")
def step_tailor_again(context):
    """A different draft, so the words actually change.

    Re-tailoring to the same words would leave the fingerprint identical and
    the approval standing, which is correct but tests nothing.
    """
    draft = _swap_experience(context.master)
    set_draft(context, draft.replace("- Ran the release process every week\n", ""))
    run(context, "tailor", context.ref, "--provider", context.provider)
    assert context.exit_code == 0, context.output


@when("I tailor my resume for a posting that does not exist")
def step_tailor_missing(context):
    run(context, "tailor", "no-such-posting", "--provider", context.provider)


@then("a resume should be written for that posting at version {version:d}")
def step_written(context, version):
    path = tailored(context, context.ref, version)
    assert path.exists(), f"{path} is not there:\n{context.output}"
    assert path.read_text(encoding="utf-8").strip()


@then("the master resume should be unchanged")
def step_master_unchanged(context):
    on_disk = (context.home / "resumes" / "master.md").read_text(encoding="utf-8")
    assert on_disk == context.master


@then("version 1 should still say what it said")
def step_version_one_intact(context):
    assert (
        tailored(context, context.ref, 1).read_text(encoding="utf-8")
        == context.version_one
    )


@then("no resume file should have been written")
def step_nothing_written(context):
    directory = context.home / "resumes" / context.ref
    written = list(directory.glob("v*.md")) if directory.exists() else []
    assert not written, f"these were written anyway: {written}"


@then("the draft should be accepted")
def step_accepted(context):
    assert context.exit_code == 0, context.output


@then("scout should refuse the draft")
def step_draft_refused(context):
    assert context.exit_code == 1, context.output
    assert "Refused the draft" in context.output, context.output


@then('scout should say "{term}" is not in the master resume')
def step_names_term(context, term):
    assert f'"{term}" is not in the master resume' in context.output, context.output


@then("scout should show me the draft it refused")
def step_shows_draft(context):
    assert "The draft is below" in context.output, context.output
    assert "## Skills" in context.output, context.output


@then("scout should tell me I can tailor again")
def step_says_tailor_again(context):
    assert "tailor again" in context.output, context.output


@then('the tailored resume should lead with "{skill}"')
def step_leads_with(context, skill):
    written = tailored(context, context.ref, 1).read_text(encoding="utf-8")
    body = written.split("## Skills", 1)[1]
    assert body.index(skill) < body.index("Python"), body[:200]


@then("scout should summarise what changed")
def step_summarises(context):
    assert "What changed:" in context.output, context.output


@then("the summary should name what it moved up")
def step_moved_up(context):
    assert "moved up" in context.output, context.output


@then("the summary should name what it played down")
def step_played_down(context):
    assert "played down" in context.output, context.output


@then("the summary should show the claim it rewrote")
def step_shows_rewrite(context):
    assert "rewritten" in context.output, context.output
    assert "12" in context.output, context.output


@then("the summary should say what changed for every section it touched")
def step_every_section(context):
    for employer in context.employers:
        assert employer in context.output, f"{employer} missing from:\n{context.output}"


@then("scout should say where it looked for the master resume")
def step_where_master(context):
    assert "resumes/master.md" in context.output, context.output


@then("scout should say the master resume had nothing in it")
def step_master_empty(context):
    assert "nothing in it" in context.output, context.output


@then("scout should name the variable it expects")
def step_names_variable(context):
    assert "OPENROUTER_API_KEY" in context.output, context.output


@then("scout should say the dates are not what the master gives that employer")
def step_dates_refused(context):
    assert "is not a date the master resume gives for" in context.output, context.output


@then("scout should say the model call failed")
def step_model_failed(context):
    assert "model call failed" in context.output, context.output
