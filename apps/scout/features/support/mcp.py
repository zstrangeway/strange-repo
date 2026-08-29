"""A real MCP client, talking to a real scout server over a real pipe.

behave is synchronous and an MCP session is not, so the session lives in an
event loop on its own thread and steps hand it coroutines. The alternative —
standing the server up and tearing it down inside every step — would test a
server that has only ever answered one call, and "the server should still be
running" would mean nothing.

The server is a subprocess on purpose. A stray print in a startup path, a slow
import, a missing entry point: none of those are visible to anything that
imports the module and calls its functions, and every one of them reaches a
person as "server disconnected" with nothing to read.
"""

import asyncio
import contextlib
import os
import threading
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

APP_ROOT = Path(__file__).resolve().parents[2]

# Coverage does not follow a subprocess unless the subprocess starts it. This
# is the documented way: sitecustomize.py in the app root calls
# coverage.process_startup(), which does nothing unless COVERAGE_PROCESS_START
# is set — so a plain `scout-mcp` outside the suite is unaffected.
SUBPROCESS_ENVIRONMENT = {
    "COVERAGE_PROCESS_START": str(APP_ROOT / "pyproject.toml"),
    "PYTHONPATH": str(APP_ROOT),
}


class McpHarness:
    """One server process and one client session, for the length of a scenario."""

    def __init__(self, command: str, args: list[str], errlog_path: Path) -> None:
        self.errlog_path = errlog_path
        self.errlog = errlog_path.open("w", encoding="utf-8")
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.stack = AsyncExitStack()
        self.parameters = StdioServerParameters(
            command=command,
            args=args,
            env={**os.environ, **SUBPROCESS_ENVIRONMENT},
            cwd=str(APP_ROOT),
        )
        self.session: ClientSession = self.run(self._open())

    def run(self, coroutine, timeout: float = 60.0):
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop).result(timeout)

    async def _open(self) -> ClientSession:
        read, write = await self.stack.enter_async_context(
            stdio_client(self.parameters, errlog=self.errlog)
        )
        session = await self.stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        return session

    def list_tools(self):
        return self.run(self.session.list_tools()).tools

    def call(self, name: str, arguments: dict):
        return self.run(self.session.call_tool(name, arguments))

    def stderr(self) -> str:
        self.errlog.flush()
        return self.errlog_path.read_text(encoding="utf-8")

    def close(self) -> None:
        # Teardown of a pipe the server may already have dropped. Nothing
        # useful is left to do about it, and raising here would bury whatever
        # the scenario was actually failing on.
        with contextlib.suppress(Exception):
            self.run(self.stack.aclose(), timeout=20.0)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=5)
        self.errlog.close()
