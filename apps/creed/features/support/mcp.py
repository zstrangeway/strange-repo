"""A real MCP client, driving a real creed server over a real stdio pipe.

In-process calls would not catch the things that actually break a stdio
server: a stray print on stdout, a slow import, a missing entry point. Each of
those reaches a person as "server disconnected" and nothing to read, so the
specs pay for a subprocess.
"""

import asyncio
import contextlib
import os
import pathlib
import threading

APP_ROOT = pathlib.Path(__file__).resolve().parents[2]

# Coverage does not follow a subprocess on its own, and every line of the MCP
# server would otherwise read as uncovered while the specs driving it pass.
# This is the documented way: sitecustomize.py in the app root calls
# coverage.process_startup(), which does nothing unless COVERAGE_PROCESS_START
# is set.
COVERAGE_ENVIRONMENT = {
    "COVERAGE_PROCESS_START": str(APP_ROOT / "pyproject.toml"),
    "PYTHONPATH": str(APP_ROOT),
}


class McpHarness:
    """Starts creed-mcp, keeps it up, and calls tools on it synchronously.

    behave's steps are synchronous and the SDK's client is not, so the loop
    runs on its own thread and every call is handed to it.
    """

    @classmethod
    def from_command(
        cls, command: list[str], environment, stderr_path: str, cwd: str | None = None
    ):
        """Start a server from a literal command line.

        Used by the spec that runs the README's own config block, so that the
        thing people paste into Claude Code is the thing that is tested.
        """
        return cls(environment, stderr_path, command=command, cwd=cwd)

    def __init__(
        self,
        environment: dict[str, str],
        stderr_path: str,
        command: list[str] | None = None,
        cwd: str | None = None,
    ) -> None:
        self._command = command or ["uv", "run", "--quiet", "creed-mcp"]
        self._cwd = cwd or os.getcwd()
        self._environment = {**environment, **COVERAGE_ENVIRONMENT}
        self._stderr_path = stderr_path
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._session = None
        self._exit = None
        self._errlog = None
        self.stdout_frames: list[str] = []
        self._run(self._start())

    def _run(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop).result(120)

    async def _start(self) -> None:
        from contextlib import AsyncExitStack

        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        # Deliberately not a context manager: the file has to outlive this
        # coroutine, because the server writes to it for as long as it runs.
        self._errlog = open(self._stderr_path, "w", buffering=1)  # noqa: SIM115
        parameters = StdioServerParameters(
            command=self._command[0],
            args=self._command[1:],
            env=self._environment,
            cwd=self._cwd,
        )
        self._exit = AsyncExitStack()
        # errlog belongs to stdio_client, not to the parameters object. Passed
        # in the wrong place it is silently ignored and the client defaults to
        # sys.stderr — which behave has replaced with a StringIO, so starting
        # the subprocess dies on `fileno`.
        read, write = await self._exit.enter_async_context(
            stdio_client(parameters, errlog=self._errlog)
        )
        self._session = await self._exit.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

    def tools(self) -> list:
        return self._run(self._session.list_tools()).tools

    def call(self, name: str, arguments: dict | None = None):
        result = self._run(self._session.call_tool(name, arguments or {}))
        text = "\n".join(
            block.text for block in result.content if getattr(block, "text", None)
        )
        return result.is_error, text

    def alive(self) -> bool:
        """A refusal must not have taken the server with it."""
        try:
            return bool(self.tools())
        except Exception:
            return False

    def stderr(self) -> str:
        if self._errlog is not None:
            self._errlog.flush()
        try:
            with open(self._stderr_path) as handle:
                return handle.read()
        except FileNotFoundError:
            return ""

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self._run(self._exit.aclose())
        if self._errlog is not None:
            self._errlog.close()
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
