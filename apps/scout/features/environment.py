"""Everything a scenario needs, and nothing it does not.

Each scenario gets its own directory: a fresh SQLite file, a fresh `resumes/`,
and `SCOUT_HOME` pointed at it. Nothing survives a scenario, so no scenario
can pass because of one that ran before it.

The provider is stubbed for every scenario. No tier of this repo calls a real
model — `task scout:smoke` is the opt-in command that does, and its output is
read rather than its exit code.
"""

import os
import shutil
import tempfile
from pathlib import Path

from support.board import JobBoard
from support.mcp import McpHarness

# Restored between scenarios so that one setting a key, a draft or a failure
# cannot leak into the next.
MANAGED = (
    "SCOUT_HOME",
    "SCOUT_FETCH_TIMEOUT",
    "SCOUT_MODEL",
    "ANTHROPIC_API_KEY",
)


def before_scenario(context, scenario):
    context.saved_environment = {name: os.environ.get(name) for name in MANAGED}
    context.home = Path(tempfile.mkdtemp(prefix="scout-spec-"))
    os.environ["SCOUT_HOME"] = str(context.home)
    # A board that never answers should cost a scenario a second, not fifteen.
    os.environ["SCOUT_FETCH_TIMEOUT"] = "1"
    # Set so that nothing reaches Anthropic even if a step reaches for the
    # real provider by mistake. The specs use the fake one.
    os.environ["ANTHROPIC_API_KEY"] = "not-a-real-key"

    context.board = None
    context.mcp = None
    context.exit_code = None
    context.output = ""
    context.master = None
    # The stub, everywhere except the scenario about a missing key: that one
    # needs the real provider, which refuses before it opens a connection.
    context.provider = "fake"
    # Handed to any subprocess a step spawns, so it lands in the same scratch
    # directory this scenario is using.
    context.environment = dict(os.environ)


def after_scenario(context, scenario):
    if context.mcp is not None:
        context.mcp.close()
    if context.board is not None:
        context.board.close()
    shutil.rmtree(context.home, ignore_errors=True)
    for name, value in context.saved_environment.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


__all__ = ["JobBoard", "McpHarness"]
