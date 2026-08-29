"""The provider the specs use.

Every tier of this repo stops short of a real model, for the reason gary does:
a suite that calls one is slow, costs somebody money, and is not a test of
anything, because the answer changes. `scout smoke` is the opt-in command that
plays a real one.

What comes back is whatever a scenario wrote into the scratch directory —
files rather than environment variables, because the MCP specs drive a server
in another process that was started before the scenario knew what it wanted
the model to say.
"""

from .. import paths
from ..errors import ScoutError

DRAFT_FILE = "fake-draft.md"
FAILURE_FILE = "fake-failure.txt"


class FakeProvider:
    name = "fake"

    def tailor(self, *, master: str, posting: str) -> str:
        directory = paths.database_path().parent
        failure = directory / FAILURE_FILE
        if failure.exists():
            raise ScoutError(
                f"The model call failed: {failure.read_text(encoding='utf-8').strip()}"
            )
        draft = directory / DRAFT_FILE
        if not draft.exists():
            # Reordering nothing is still a legal tailoring, and it keeps a
            # scenario that does not care about the draft from inventing one.
            return master
        return draft.read_text(encoding="utf-8")
