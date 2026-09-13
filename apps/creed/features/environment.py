"""Everything a scenario needs, and nothing it does not.

Each scenario gets its own directory and its own export site on a fresh port,
so nothing survives a scenario and no scenario can pass because of one that
ran before it.

Nothing here reaches wahapedia.ru. ``CREED_EXPORT_BASE`` points creed at the
local site, and a scenario that wanted the real export would be a spec that
fails when somebody is on a train.
"""

import os
import shutil
import tempfile
from pathlib import Path

from support.export_site import ExportSite
from support.mcp import McpHarness

MANAGED = ("CREED_HOME", "CREED_EXPORT_BASE", "CREED_SYNC_ON_START")


def before_scenario(context, scenario):
    context.saved_environment = {name: os.environ.get(name) for name in MANAGED}
    context.home = Path(tempfile.mkdtemp(prefix="creed-spec-"))
    os.environ["CREED_HOME"] = str(context.home)
    context.site = ExportSite()
    os.environ["CREED_EXPORT_BASE"] = context.site.base_url
    # The MCP specs start their own server and sync it themselves, so no
    # scenario pays for a startup sync it did not ask for.
    os.environ["CREED_SYNC_ON_START"] = "0"

    context.mcp = None
    context.result = None
    context.report = None
    context.error = None
    context.output = ""
    context.exit_code = None
    context.list_id = None
    context.unit_ids = []
    context.attack = None
    context.environment = dict(os.environ)


def after_scenario(context, scenario):
    if context.mcp is not None:
        context.mcp.close()
    context.site.close()
    shutil.rmtree(context.home, ignore_errors=True)
    for name, value in context.saved_environment.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


__all__ = ["ExportSite", "McpHarness"]
