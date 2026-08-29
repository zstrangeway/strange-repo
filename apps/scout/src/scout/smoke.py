"""One real tailoring, against a real model.

Deliberately not part of `task test`. It is the only thing here that talks to
a model, so it is run by hand and its output is read rather than its exit
code.

It exists because every tier of the suite stubs the provider, and a stub
cannot notice that the prompt stopped working — or that the grounding check
refuses something a real model legitimately wrote. The check has only ever
judged drafts somebody typed on purpose; this is the command that shows it a
draft nobody wrote.

**The default costs nothing.** Per CLAUDE.md a hand-run check names a `:free`
model, so this one does: same code path, same prompt, no money. A paid model
is opted into, and the command says what it expects to spend before it does.
"""

import argparse
import sys

from . import db, tailoring
from .errors import ScoutError
from .providers import load

# Free, and large enough to hold a resume and a posting. The model gary-api's
# own smoke record used, so the two apps' notes stay comparable.
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scout-smoke",
        description="Tailor for one posting against a real model.",
    )
    parser.add_argument("ref", help="A saved posting to tailor for")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"default {DEFAULT_MODEL}, which is free",
    )
    args = parser.parse_args(argv)

    provider = load()
    provider.model = args.model

    if args.model.endswith(":free"):
        print(f"Calling {args.model} once. It is a free model; this costs nothing.")
    else:
        # Said before it is spent, not after, because after is too late to
        # decide against it.
        print(
            f"Calling {args.model} once. A resume and a posting in, a resume "
            "out — expect a few cents."
        )

    try:
        with db.connect() as connection:
            result = tailoring.tailor(connection, args.ref, provider)
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
