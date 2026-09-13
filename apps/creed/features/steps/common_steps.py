"""Steps shared across features: getting data in, and reading what came back."""

from behave import given, then, when
from support.harness import synced

from creed import answers, db, export, sync
from creed.fetch import ExportUnreachableError


@given("a scratch creed directory")
def step_scratch(context):
    # environment.py already made one. Naming it in the feature keeps the
    # scenarios readable about what they assume.
    assert context.home.exists()


@given("creed has never synced")
def step_never_synced(context):
    state = sync.status()
    assert not state["synced"], "this scenario needs an empty database"


@given("the export is available")
def step_export_available(context):
    context.site.offline = False


@given("the export cannot be reached")
def step_export_offline(context):
    context.site.offline = True


@given("creed has a complete sync")
def step_complete_sync(context):
    synced(context)


@given("creed has a complete sync from an older timestamp")
@given("magos has a complete sync from an older timestamp")
def step_older_sync(context):
    synced(context, "2026-01-01 00:00:00")


@given("creed synced at the export's current timestamp")
def step_current_sync(context):
    synced(context)


@given("creed synced at an older timestamp")
def step_synced_older(context):
    synced(context, "2026-01-01 00:00:00")


@given("the export has since been updated")
def step_export_updated(context):
    # A real update moves the marker *and* changes something. Moving only the
    # marker would leave every table's ETag intact, and creed downloading
    # nothing would then be the correct answer rather than a bug — which is
    # what the first version of this step actually asserted against.
    context.site.set_last_update("2026-06-06 12:00:00")
    context.site.change_price("D1", " 100", "110")


@given("creed has a complete sync from well over a week ago")
def step_old_sync(context):
    synced(context)
    with db.session() as connection:
        db.set_state(connection, sync.LAST_CHECKED_KEY, "2020-01-01T00:00:00+00:00")


@when("creed syncs")
def step_sync(context):
    try:
        context.result = sync.sync()
        context.error = None
    except ExportUnreachableError as error:
        context.result = None
        context.error = error


@when("creed checks for updates")
def step_check(context):
    context.site.reset_requests()
    context.check = sync.check()


@then("every export table should be in the database")
def step_all_tables(context):
    state = sync.status()
    expected = {table.name for table in export.data_tables()}
    assert set(state["tables"]) == expected, set(state["tables"]) ^ expected
    assert all(count > 0 for count in state["tables"].values()), state["tables"]


@then("the database should record the export's update timestamp")
def step_records_stamp(context):
    state = sync.status()
    assert state["last_update"], state


@then("creed should have fetched every table the export's specification names")
def step_fetched_all(context):
    fetched = set(context.site.downloads())
    expected = {table.name for table in export.data_tables()}
    assert expected <= fetched, expected - fetched


@then("a table in the specification that creed did not fetch should fail the sync")
def step_missing_table_fails(context):
    # The specification is the authority: a table named there that the site
    # does not serve must break the sync rather than leave a silent hole.
    del context.site.tables["Detachments"]
    result = sync.sync(force=True)
    assert result.failed, "a missing table passed silently"
    assert "Detachments" in result.failed, result.failed


@then("creed should have fetched only the update marker")
def step_only_marker(context):
    assert context.site.downloads() == [], context.site.downloads()


@then("creed should not have downloaded any table")
def step_no_downloads(context):
    assert context.site.downloads() == [], context.site.downloads()


@then("creed should download the tables again")
def step_downloaded(context):
    assert context.check["stale"], context.check
    result = sync.sync()
    assert result.downloaded, "nothing was downloaded"


@then("the database should record the new timestamp")
def step_new_stamp(context):
    assert sync.status()["last_update"] == "2026-06-06 12:00:00", sync.status()


@then("creed should answer from what it has")
def step_answers_anyway(context):
    with db.session() as connection:
        provenance = answers.provenance(connection)
    assert provenance.last_update
    context.provenance = provenance


@then("the answer should say when the data was last synced")
def step_says_when(context):
    assert context.provenance.last_update


@then("creed should say it has no data yet")
def step_no_data(context):
    assert context.error is not None, "creed answered when it had nothing"
    assert "no data yet" in str(context.error).lower(), context.error


@then("creed should say how to sync")
def step_says_how(context):
    assert "creed sync" in str(context.error), context.error


@then("creed should say it could not reach the export")
def step_says_offline(context):
    assert context.site.offline
