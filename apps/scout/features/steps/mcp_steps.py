"""The MCP surface: a real client, a real pipe, a real server process."""

import json
import re
import subprocess

from behave import given, then, when
from support.cli import run
from support.mcp import APP_ROOT, SUBPROCESS_ENVIRONMENT, McpHarness

README = APP_ROOT / "README.md"

SERVER_COMMAND = ("uv", "run", "--directory", str(APP_ROOT), "scout-mcp")


@given("scout's MCP server running over stdio")
def step_server(context):
    context.mcp = McpHarness(
        SERVER_COMMAND[0],
        list(SERVER_COMMAND[1:]),
        context.home / "server-stderr.log",
    )


@when("I ask the server what tools it has")
@then("the server should answer what tools it has")
def step_list_tools(context):
    context.tools = context.mcp.list_tools()
    assert context.tools


def _tool_named(context, fragment):
    matched = [tool for tool in context.tools if fragment in tool.name]
    assert matched, [tool.name for tool in context.tools]
    return matched[0]


@then("the tools should include one for saving a posting")
def step_has_save(context):
    _tool_named(context, "save_posting")


@then("the tools should include one for tailoring a resume")
def step_has_tailor(context):
    _tool_named(context, "tailor_resume")


@then("the tools should include one for logging a status")
def step_has_log(context):
    _tool_named(context, "log_status")


@then("the tools should include one for listing postings")
def step_has_list(context):
    _tool_named(context, "list_postings")


@then("every tool should describe what it does")
def step_tools_described(context):
    for tool in context.tools:
        assert tool.description and len(tool.description) > 40, tool.name


@then("every tool should declare the arguments it takes")
def step_tools_schema(context):
    for tool in context.tools:
        assert tool.input_schema.get("type") == "object", tool.name
        assert "properties" in tool.input_schema, tool.name


# ------------------------------------------------------------------- calling


def _call(context, name, arguments):
    context.reply = context.mcp.call(name, arguments)
    context.reply_text = "\n".join(
        block.text for block in context.reply.content if block.type == "text"
    )
    return context.reply


@when('I call the save tool with a pasted posting for "{title}" at "{company}"')
def step_call_save(context, title, company):
    body = (
        f"{title} at {company}. We are looking for somebody to own the "
        "platform, working in Python against Postgres, with Terraform "
        "describing the infrastructure underneath it."
    )
    _call(
        context,
        "save_posting",
        {"text": body, "title": title, "company": company},
    )
    match = re.search(r"Saved (\S+)", context.reply_text)
    if match:
        context.ref = match.group(1).rstrip(":")


@when("I call the tailor tool for that posting")
def step_call_tailor(context):
    _call(context, "tailor_resume", {"ref": context.ref, "provider": "fake"})


@when("I call the tailor tool with no posting at all")
def step_call_tailor_bare(context):
    _call(context, "tailor_resume", {})


@when('I call the log tool for that posting with "{status}" noting "{note}"')
def step_call_log(context, status, note):
    _call(context, "log_status", {"ref": context.ref, "status": status, "note": note})


@when('I call the log tool for a posting that does not exist with "{status}"')
def step_call_log_missing(context, status):
    _call(context, "log_status", {"ref": "no-such-posting", "status": status})


@then("the call should succeed")
def step_call_ok(context):
    assert not context.reply.is_error, context.reply_text


@then("the call should report a failure")
def step_call_failed(context):
    assert context.reply.is_error, context.reply_text


@then("the reply should name the posting's reference")
def step_reply_ref(context):
    assert context.ref and context.ref in context.reply_text, context.reply_text


@then("the reply should say where the resume was written")
def step_reply_path(context):
    assert "Wrote " in context.reply_text, context.reply_text
    assert ".md" in context.reply_text, context.reply_text


@then("the reply should summarise what changed")
def step_reply_summary(context):
    assert "What changed:" in context.reply_text, context.reply_text


@then('the reply should say "{term}" is not in the master resume')
def step_reply_invented(context, term):
    assert f'"{term}" is not in the master resume' in context.reply_text, (
        context.reply_text
    )


@then("the reply should say no such posting")
def step_reply_no_posting(context):
    assert "no posting called" in context.reply_text, context.reply_text


@then("the posting should be in the database")
def step_in_database(context):
    run(context, "show", context.ref)
    assert context.exit_code == 0, context.output


@then("the server should still be running")
def step_still_running(context):
    assert context.mcp.list_tools(), "the server stopped answering"


# -------------------------------------------------------------- the pipe itself


@then("everything the server wrote to stdout should be protocol frames")
def step_stdout_clean(context):
    """Drive a server by hand and read every byte it writes to stdout.

    The client session cannot check this: a malformed line is dropped by the
    transport and the session carries on, so the one thing that breaks a real
    Claude Code connection is the one thing it would not notice.
    """
    process = subprocess.Popen(
        SERVER_COMMAND,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(APP_ROOT),
        env={**context.environment, **SUBPROCESS_ENVIRONMENT},
    )
    handshake = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "spec", "version": "0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    stdout, _ = process.communicate(
        "\n".join(json.dumps(message) for message in handshake) + "\n", timeout=90
    )
    lines = [line for line in stdout.splitlines() if line.strip()]
    assert lines, "the server said nothing at all"
    for line in lines:
        message = json.loads(line)  # raises if anything else got printed
        assert message.get("jsonrpc") == "2.0", line


@then("the server's own log lines should have gone to stderr")
def step_logs_on_stderr(context):
    assert "tool.call" in context.mcp.stderr(), context.mcp.stderr()


# ------------------------------------------------------ the README's own block


@given("the command in the README's Claude Code config block")
def step_readme_command(context):
    """Read the block a person pastes into Claude Code, and use exactly it.

    If it drifts from what the package installs, the first thing anybody does
    with scout fails — so the spec reads the README rather than a copy of it.
    """
    block = re.search(r"```json\n(.*?)```", README.read_text(encoding="utf-8"), re.S)
    assert block, "no json block in the README"
    config = json.loads(block.group(1))
    server = config["mcpServers"]["scout"]
    context.readme_command = [server["command"], *server["args"]]


@when("I start a server with exactly that command")
def step_start_readme_server(context):
    command = [
        # The README names the directory somebody clones into; the spec knows
        # where this checkout actually is. Nothing else is substituted.
        str(APP_ROOT) if argument == "/absolute/path/to/apps/scout" else argument
        for argument in context.readme_command
    ]
    context.mcp.close()
    context.mcp = McpHarness(
        command[0], command[1:], context.home / "readme-server-stderr.log"
    )
