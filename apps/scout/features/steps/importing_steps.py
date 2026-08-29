"""Getting a real resume in."""

from behave import given, then, when
from support.cli import run

RESUME = """Ada Lovelace
ada@example.com

Technical Skills:
Languages: Python, TypeScript
Cloud: AWS, Docker

Experience:
Wilding Labs - Senior Engineer (2021 - 2025)
Ran the Postgres upgrade across forty services
Led a team of three through the billing migration

Thornfield Systems - Platform Engineer (2018 - 2021)
Built the Python services behind billing
"""

# What a model returns: the same words, with markdown around them.
STRUCTURED = """# Ada Lovelace

ada@example.com

## Technical Skills

Languages: Python, TypeScript
Cloud: AWS, Docker

## Experience

### Wilding Labs — Senior Engineer

2021 - 2025

- Ran the Postgres upgrade across forty services
- Led a team of three through the billing migration

### Thornfield Systems — Platform Engineer

2018 - 2021

- Built the Python services behind billing
"""


def _source(context):
    path = context.home / "resume.txt"
    path.write_text(context.resume, encoding="utf-8")
    return path


def _model_returns(context, markdown):
    directory = context.home / ".scout"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "fake-structured.md").write_text(markdown, encoding="utf-8")


@given("a resume file with two employers and a skills section")
def step_resume_file(context):
    context.resume = RESUME
    _model_returns(context, STRUCTURED)


@given("a resume file whose name is repeated as a page header")
def step_resume_with_header(context):
    # Three pages, each stamped with the name and a number, as a PDF hands it
    # over.
    context.resume = RESUME + "\nAda Lovelace\n2\nAda Lovelace\n3\n"
    _model_returns(context, STRUCTURED)


@given("the model will return it with a job missing")
def step_model_drops(context):
    _model_returns(
        context, STRUCTURED.split("### Thornfield Systems")[0].rstrip() + "\n"
    )


@given("the model will return it with a skill added")
def step_model_invents(context):
    _model_returns(
        context, STRUCTURED.replace("AWS, Docker", "AWS, Docker, Kubernetes")
    )


@when("I import it")
@given("I have already imported it")
def step_import(context):
    run(context, "import", _source(context), "--provider", "fake")


@when("I import it again")
def step_import_again(context):
    run(context, "import", _source(context), "--provider", "fake")


@when("I import it again, replacing what is there")
def step_import_replacing(context):
    run(context, "import", _source(context), "--provider", "fake", "--replace")


@when("I import a file that does not exist")
def step_import_missing(context):
    run(context, "import", context.home / "nowhere.pdf", "--provider", "fake")


@then("a master resume should be written")
def step_master_written(context):
    assert (context.home / "resumes" / "master.md").exists(), context.output


@then("no master resume should have been written")
def step_no_master_written(context):
    assert not (context.home / "resumes" / "master.md").exists(), context.output


@then("it should have both employers as headings")
def step_both_employers(context):
    written = (context.home / "resumes" / "master.md").read_text(encoding="utf-8")
    assert "### Wilding Labs" in written, written
    assert "### Thornfield Systems" in written, written


@then("the master resume should still have the name in it")
def step_name_survives(context):
    written = (context.home / "resumes" / "master.md").read_text(encoding="utf-8")
    assert "Ada Lovelace" in written, written


@then("scout should say how many employers it found")
def step_says_employer_count(context):
    assert "2 employer(s)" in context.output, context.output


@then("scout should say every word survived and none were added")
def step_says_conserved(context):
    assert "every word of the original survived" in context.output, context.output
    assert "none were added" in context.output, context.output


@then("scout should tell me to read the result")
def step_says_read_it(context):
    assert "Read it before you tailor" in context.output, context.output
    assert "structure is not" in context.output, context.output


@then("scout should say what it dropped")
def step_says_dropped(context):
    assert "dropped" in context.output, context.output
    listed = context.output.split("word(s):", 1)[1].split(".")[0].split()
    assert listed, context.output
    # Every word named has to be one the resume actually had, or the refusal
    # is telling somebody to look for something that was never there.
    for word in listed:
        assert word in context.resume.lower(), f"{word} was not in the resume"


@then("scout should say what it added")
def step_says_added(context):
    assert "added" in context.output, context.output
    assert "kubernetes" in context.output.lower(), context.output


@then("scout should say the master resume is already there")
def step_says_already_there(context):
    assert "already a master resume" in context.output, context.output


@then("scout should say where it looked")
def step_says_where_it_looked(context):
    assert "no file at" in context.output, context.output
