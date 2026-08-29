"""One real tailoring, against a real model.

Deliberately not part of `task test`. It costs money, needs a key, and is the
only thing here that talks to a model — so it is run by hand, and its output
is read rather than its exit code.

It exists because every tier of the suite stubs the provider, and a stub
cannot notice that the prompt stopped working. This is the only way to see
what a model actually does with the instruction not to invent anything.
"""

import argparse
import sys

from . import db, tailoring
from .errors import ScoutError
from .providers.anthropic_api import DEFAULT_MODEL, AnthropicProvider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scout-smoke",
        description="Tailor for one posting against a real model.",
    )
    parser.add_argument("ref", help="A saved posting to tailor for")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args(argv)

    print(f"About to call {args.model} once. A resume-sized call is a few cents.")
    try:
        with db.connect() as connection:
            result = tailoring.tailor(
                connection, args.ref, AnthropicProvider(model=args.model)
            )
    except ScoutError as error:
        # A refusal here is a result, not a failure: it means the grounding
        # check caught a real model inventing something, which is exactly what
        # this command is for seeing.
        print(str(error), file=sys.stderr)
        return 1
    print(result.render())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
