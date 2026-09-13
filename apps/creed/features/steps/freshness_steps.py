"""Steps for the feature the app exists for."""

from behave import given, then, when

from creed import answers, datasheets, db, export, sync
from creed.fetch import ExportUnreachableError


@given("only the points table actually differs")
def step_only_points_differ(context):
    # The update above already moved exactly one table. Named as its own step
    # because the scenario is about what creed pays for, and that only means
    # something if the scenario says what changed.
    assert "110" in context.site.tables["Datasheets_models_cost"]


@given("one table comes back with columns creed does not recognise")
def step_broken_table(context):
    context.site.broken_table = "Stratagems"


@when("the sync fails partway through")
def step_sync_fails(context):
    # Six tables in, which is far enough to have written some and not others
    # had the sync been writing to the live database.
    context.site.fail_after = 6
    context.result = sync.sync()


@when("I look up any datasheet")
@when("I look up a datasheet")
def step_look_up(context):
    try:
        with db.session() as connection:
            provenance = answers.provenance(connection)
            context.sheets = datasheets.by_name(connection, "Testudo Guard")
            context.provenance = provenance
            context.error = None
    except answers.NotSyncedError as error:
        context.error = error
        context.provenance = None


@then("the unchanged tables should have come back as not-modified")
def step_not_modified(context):
    assert context.result.not_modified, "every table was re-downloaded"
    assert len(context.result.not_modified) >= len(export.data_tables()) - 1, (
        context.result.not_modified
    )


@then("only the points table should have been downloaded in full")
def step_only_points_downloaded(context):
    assert context.result.downloaded == ["Datasheets_models_cost"], (
        context.result.downloaded
    )


@then("creed should still answer from the older complete data")
def step_older_data(context):
    state = sync.status()
    assert state["last_update"] == "2026-01-01 00:00:00", state["last_update"]
    with db.session() as connection:
        sheets = datasheets.by_name(connection, "Testudo Guard")
    assert sheets, "the older data did not survive"


@then("the recorded timestamp should still be the older one")
def step_stamp_unchanged(context):
    assert sync.status()["last_update"] == "2026-01-01 00:00:00"


@then("creed should report that the sync failed")
def step_reports_failure(context):
    assert context.result.failed, "the sync reported success"


@then("creed should name the table it could not read")
def step_names_table(context):
    assert "Stratagems" in (context.result.failed or ""), context.result.failed


@then("the answer should carry the export's update timestamp")
def step_answer_has_stamp(context):
    assert context.provenance.last_update == sync.status()["last_update"]


@then("the answer should warn that the data may be behind")
def step_warns_stale(context):
    assert context.provenance.warnings, "no staleness warning"
    assert "behind" in context.provenance.warnings[0]


@then("the answer should credit Wahapedia")
def step_credits(context):
    assert "Wahapedia" in context.provenance.attribution


@then("the answer should link to the datasheet on Wahapedia")
def step_links(context):
    assert context.sheets, "no datasheet to link to"
    assert context.sheets[0].link.startswith("http"), context.sheets[0].link


@when("creed tries to sync with the export down")
def step_sync_offline(context):
    try:
        context.result = sync.sync()
        context.error = None
    except ExportUnreachableError as error:
        context.error = error
