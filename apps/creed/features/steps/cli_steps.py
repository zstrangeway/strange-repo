"""Steps for creed on the command line."""

from behave import then, when
from support.cli import run

from creed import army, datasheets, db


@when("I run the sync")
def step_run_sync(context):
    run(context, "sync")


@when("I ask for the data's status")
def step_run_status(context):
    run(context, "status")


@when('I look up "Testudo Guard" on the command line')
def step_run_show(context):
    run(context, "show", "Testudo Guard", "--faction", "Test Guard")


@when("I start a list, add two units and check it")
def step_run_list_flow(context):
    run(context, "list", "new", "cli-list", "Test Guard", "--points", "2000")
    with db.session() as connection:
        context.list_id = army.all_lists(connection)[0]["id"]
        sheet = datasheets.by_name(connection, "Testudo Guard", "Test Guard")[0]
    run(context, "list", "add", str(context.list_id), sheet.id, "--models", "5")
    run(context, "list", "add", str(context.list_id), sheet.id, "--models", "5")
    context.added_output = context.output
    run(context, "list", "check", str(context.list_id))


@when("I run any command that changes something")
def step_run_changing(context):
    # Needs data first: starting a list checks the faction against the export.
    run(context, "sync")
    run(context, "list", "new", "changed-list", "Test Guard", "--points", "1000")


@then("creed should say how many rows it loaded")
def step_says_rows(context):
    assert "rows" in context.output, context.output


@then("creed should say what the export's update timestamp is")
def step_says_stamp(context):
    assert "2026" in context.output, context.output


@then("creed should say the data was already current")
def step_says_current(context):
    assert "Already current" in context.output, context.output


@then("creed should say when it was last updated")
def step_says_updated(context):
    assert "2026" in context.output, context.output


@then("creed should say the export's update timestamp")
def step_status_stamp(context):
    assert "Export last updated" in context.output, context.output


@then("creed should say when it last checked")
def step_status_checked(context):
    assert "last checked" in context.output, context.output


@then("creed should say how many rows it holds")
def step_status_rows(context):
    assert "Rows held" in context.output, context.output


@then("I should get its statline, weapons and abilities")
def step_cli_datasheet(context):
    for heading in ("Statlines", "Weapons", "Abilities"):
        assert heading in context.output, context.output


@then("I should get the total and the check's report")
def step_cli_report(context):
    assert "Total" in context.added_output or "Total" in context.output
    assert "List check" in context.output, context.output


@then("creed should say to sync first")
def step_says_sync_first(context):
    assert "creed sync" in context.stderr, context.stderr


@then("creed should exit non-zero")
def step_nonzero(context):
    assert context.exit_code != 0, context.exit_code


@then("creed should say what changed")
def step_says_changed(context):
    assert context.output.strip(), "the command said nothing"
