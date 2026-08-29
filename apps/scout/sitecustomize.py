"""Starts coverage inside a subprocess the suite spawns.

`coverage.process_startup()` is a no-op unless COVERAGE_PROCESS_START is set,
which the MCP harness sets and nothing else does. So this file costs a plain
`scout-mcp` an import and changes nothing about it — and without it, every
line of the MCP server reads as uncovered while the specs that drive it pass.
"""

try:
    import coverage
except ImportError:  # pragma: no cover — coverage is a dev dependency
    pass
else:
    coverage.process_startup()
