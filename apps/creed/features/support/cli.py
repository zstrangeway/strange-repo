"""Running creed's command line inside the scenario's own directory.

In-process rather than as a subprocess: the CLI is a thin shell over the same
modules, its exit codes are what the specs care about, and a subprocess per
scenario would pay for an interpreter start to learn nothing extra. The MCP
specs are where a real process earns its keep.
"""

import contextlib
import io

from creed import cli


def run(context, *argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            context.exit_code = cli.main(list(argv))
        except SystemExit as exit_code:  # argparse's own failures
            context.exit_code = int(exit_code.code or 0)
    context.output = out.getvalue()
    context.stderr = err.getvalue()
    return context.output
