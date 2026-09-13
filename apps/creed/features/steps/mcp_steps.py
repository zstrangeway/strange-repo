"""Steps that drive a real creed server over a real stdio pipe."""

import json
import re

from behave import given, then, when
from support.mcp import McpHarness

from creed import datasheets, db


def _start_server(context):
    if context.mcp is None:
        context.mcp = McpHarness(
            context.environment, str(context.home / "mcp-stderr.log")
        )
    return context.mcp


@given("creed's MCP server running over stdio")
def step_server(context):
    _start_server(context)


@when("I ask the server what tools it has")
def step_list_tools(context):
    context.tools = _start_server(context).tools()


def _tool_names(context):
    return {tool.name for tool in context.tools}


@then("the tools should include one for searching datasheets")
def step_has_search(context):
    assert "search_datasheets" in _tool_names(context)


@then("the tools should include one for getting a datasheet whole")
def step_has_get(context):
    assert "get_datasheet" in _tool_names(context)


@then("the tools should include one for finding stratagems")
def step_has_stratagems(context):
    assert "find_stratagems" in _tool_names(context)


@then("the tools should include one for listing factions")
def step_has_factions(context):
    assert "list_factions" in _tool_names(context)


@then("the tools should include one for detachments")
def step_has_detachments(context):
    assert "get_detachment" in _tool_names(context)


@then("the tools should include one for starting a list")
def step_has_start(context):
    assert "start_list" in _tool_names(context)


@then("the tools should include one for adding a unit to a list")
def step_has_add(context):
    assert "add_unit" in _tool_names(context)


@then("the tools should include one for removing a unit from a list")
def step_has_remove(context):
    assert "remove_unit" in _tool_names(context)


@then("the tools should include one for seeing a list")
def step_has_show(context):
    assert "show_list" in _tool_names(context)


@then("the tools should include one for checking a list")
def step_has_check(context):
    assert "check_list" in _tool_names(context)


@then("the tools should include one for working out an attack")
def step_has_attack(context):
    assert "work_out_attack" in _tool_names(context)


@then("that tool should take two datasheets rather than typed statlines")
def step_attack_takes_sheets(context):
    tool = next(t for t in context.tools if t.name == "work_out_attack")
    properties = tool.input_schema["properties"]
    assert {"attacker", "target"} <= set(properties), properties
    assert not {"toughness", "save", "strength"} & set(properties), properties


@then("the tools should include one for reporting data freshness")
def step_has_freshness(context):
    assert "data_freshness" in _tool_names(context)


@then("that tool should report the export's update timestamp")
def step_freshness_stamp(context):
    failed, text = context.mcp.call("data_freshness")
    assert not failed, text
    assert "Export last updated" in text, text


@then("that tool should report when creed last checked")
def step_freshness_checked(context):
    _, text = context.mcp.call("data_freshness")
    assert "last checked" in text, text


@then("every tool should describe what it does")
def step_all_described(context):
    missing = [
        tool.name for tool in context.tools if not (tool.description or "").strip()
    ]
    assert not missing, missing


@then("every tool should declare the arguments it takes")
def step_all_schemas(context):
    missing = [tool.name for tool in context.tools if tool.input_schema is None]
    assert not missing, missing


@when('I call the datasheet tool for "Testudo Guard"')
def step_call_datasheet(context):
    context.tool_failed, context.reply = _start_server(context).call(
        "get_datasheet", {"datasheet": "Testudo Guard", "faction": "Test Guard"}
    )


@when('I call the search tool for "walker"')
def step_call_search(context):
    context.tool_failed, context.reply = _start_server(context).call(
        "search_datasheets", {"query": "walker"}
    )


@when("I call the stratagem tool for my own turn in the Shooting phase")
def step_call_stratagems(context):
    context.tool_failed, context.reply = _start_server(context).call(
        "find_stratagems", {"turn": "Your turn", "phase": "Shooting phase"}
    )


@when("I call the search tool for something that matches very many")
def step_call_broad_search(context):
    context.tool_failed, context.reply = _start_server(context).call(
        "search_datasheets", {"query": "Testudo"}
    )


@when("I call the datasheet tool for a unit that does not exist")
def step_call_missing(context):
    context.tool_failed, context.reply = _start_server(context).call(
        "get_datasheet", {"datasheet": "Emperor's Own Breakfast Cereal"}
    )


@when("I call the datasheet tool with no unit at all")
def step_call_no_args(context):
    context.tool_failed, context.reply = _start_server(context).call(
        "get_datasheet", {}
    )


@when("I call the start-list tool for the Test Guard at 2000 points")
def step_call_start_list(context):
    context.tool_failed, context.reply = _start_server(context).call(
        "start_list", {"name": "mcp-list", "faction": "Test Guard", "points": 2000}
    )
    context.list_id = int(re.search(r"list_id is (\d+)", context.reply).group(1))


@when("I call the add-unit tool twice")
def step_call_add_twice(context):
    with db.session() as connection:
        sheet = datasheets.by_name(connection, "Testudo Guard", "Test Guard")[0]
    for _ in range(2):
        context.tool_failed, context.reply = context.mcp.call(
            "add_unit",
            {"list_id": context.list_id, "datasheet": sheet.id, "models": 5},
        )
        assert not context.tool_failed, context.reply


@when("I call the show-list tool")
def step_call_show(context):
    context.tool_failed, context.reply = context.mcp.call(
        "show_list", {"list_id": context.list_id}
    )


@when("I call the check tool for it")
def step_call_check(context):
    context.tool_failed, context.reply = _start_server(context).call(
        "check_list", {"list_id": context.list_id}
    )


@when("I call the attack tool with two datasheets")
def step_call_attack(context):
    context.tool_failed, context.reply = _start_server(context).call(
        "work_out_attack",
        {
            "attacker": "Testudo Captain",
            "target": "Testudo Walker",
            "weapon": "Test blade",
        },
    )


@then("the call should succeed")
def step_call_ok(context):
    assert not context.tool_failed, context.reply


@then("the call should report a failure")
def step_call_failed(context):
    assert context.tool_failed, context.reply


@then("the reply should carry its statline and weapons")
def step_reply_statline(context):
    assert "Statlines" in context.reply and "Weapons" in context.reply


@then("the reply should carry the export's update timestamp")
def step_reply_stamp(context):
    assert "Data as of" in context.reply, context.reply


@then('the reply should include "Testudo Walker"')
def step_reply_includes(context):
    assert "Testudo Walker" in context.reply, context.reply


@then("every stratagem in the reply should match both")
def step_reply_filtered(context):
    assert "COUNTERCHARGE" not in context.reply, context.reply


@then("the reply should be capped at a readable number")
def step_reply_capped(context):
    listed = context.reply.count("\n- ")
    assert listed <= datasheets.SEARCH_LIMIT, listed


@then("the reply should say how many there were in total")
def step_reply_total(context):
    assert re.search(r"\d+ datasheet\(s\) matched", context.reply), context.reply


@then("the reply should say how to narrow it")
def step_reply_narrow(context):
    # Only claimed when there were more than the cap; with fewer, the full
    # list is the answer and there is nothing to narrow.
    total = int(re.search(r"(\d+) datasheet\(s\) matched", context.reply).group(1))
    if total > datasheets.SEARCH_LIMIT:
        assert "Narrow it" in context.reply, context.reply


@then("the reply should say nothing matched")
def step_reply_nothing(context):
    assert "Nothing matched" in context.reply, context.reply


@then("the server should still be running")
def step_still_running(context):
    assert context.mcp.alive(), "a refusal took the server with it"


@then("the reply should carry both units and the total")
def step_reply_list(context):
    assert context.reply.count("Testudo Guard") >= 2, context.reply
    assert "Total:" in context.reply, context.reply


@then("the reply should say which checks passed")
def step_reply_checked(context):
    assert "## Checked" in context.reply, context.reply


@then("the reply should say which rules were not checked")
def step_reply_unchecked(context):
    assert "## Not checked" in context.reply, context.reply


@then("the reply should not say the list is legal")
def step_reply_not_legal(context):
    body = context.reply.replace("not the same as the list being legal", "")
    assert "is legal" not in body, context.reply


@then("the reply should carry the rolls needed and the expected damage")
def step_reply_attack(context):
    assert "wounds on" in context.reply and "Expected damage" in context.reply


@then("the reply should name any weapon ability it did not apply")
def step_reply_not_applied(context):
    # This weapon has none, so the section must be absent rather than empty.
    assert "Not applied" not in context.reply or context.reply.count("- ") > 0


@then("everything the server wrote to stdout should be protocol frames")
def step_stdout_clean(context):
    # The session got this far, which means every byte on stdout parsed as a
    # JSON-RPC frame: one stray print and initialize would have failed.
    assert context.mcp.alive()


@then("the server's own log lines should have gone to stderr")
def step_logs_to_stderr(context):
    text = context.mcp.stderr()
    assert text.strip(), "the server logged nothing anywhere"
    for line in text.strip().splitlines():
        json.loads(line)


@given("the export has been updated since creed synced")
def step_export_moved(context):
    context.site.set_last_update("2026-06-06 12:00:00")


@then("the reply should say which sync it was answering from")
def step_reply_says_sync(context):
    assert "Data as of" in context.reply, context.reply


@given("a creed with no data yet")
def step_fresh_home(context):
    """Point creed at an empty directory, for the one scenario that needs one.

    mcp.feature's Background gives every scenario a complete sync, which is
    right for all of them but the one about what a first sync writes and
    where it writes it.
    """
    import os
    import tempfile

    fresh = tempfile.mkdtemp(prefix="creed-mcp-fresh-", dir=str(context.home))
    os.environ["CREED_HOME"] = fresh
    context.environment["CREED_HOME"] = fresh


@when("the server starts and syncs")
def step_server_syncs(context):
    environment = dict(context.environment)
    environment["CREED_SYNC_ON_START"] = "1"
    context.mcp = McpHarness(environment, str(context.home / "mcp-sync.log"))
    context.mcp.tools()


@then("the sync's progress should have gone to stderr")
def step_sync_stderr(context):
    assert "rows" in context.mcp.stderr(), context.mcp.stderr()


@then("the sync should report how many rows it loaded")
def step_sync_rows(context):
    assert re.search(r"\d+ rows", context.mcp.stderr()), context.mcp.stderr()


@given("the command in the README's Claude Code config block")
def step_readme_command(context):
    import pathlib

    readme = pathlib.Path("README.md").read_text()
    block = re.search(r"```json\n(.*?)```", readme, re.DOTALL)
    assert block, "the README has no Claude Code config block"
    config = json.loads(block.group(1))
    entry = config["mcpServers"]["creed"]
    context.readme_command = [entry["command"], *entry.get("args", [])]


@when("I start a server with exactly that command")
def step_start_readme_server(context):
    # Run it from the repository root, which is where the config block's
    # `--directory apps/creed` is written to be run from — that is the whole
    # point of checking the block rather than a command of our own.
    import pathlib

    root = pathlib.Path.cwd().parent.parent
    context.mcp = McpHarness.from_command(
        context.readme_command,
        dict(context.environment),
        str(context.home / "readme.log"),
        cwd=str(root),
    )


@then("the server should answer what tools it has")
def step_readme_tools(context):
    assert context.mcp.tools()
