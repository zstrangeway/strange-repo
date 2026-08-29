"""The opt-in command that spends real money.

Its provider is replaced here. The point of covering it is that the command
somebody reaches for before a deploy should not fail on an argument or a
missing posting — the one time it runs is the time it matters.
"""

import unittest
import unittest.mock

from support import InAScratchHome

from scout import smoke
from scout.errors import ScoutError

MASTER = """# Ada

## Skills

Python, Postgres

## Experience

### Wilding Labs — Senior Engineer

- Ran the Postgres upgrade
"""


class Smoke(InAScratchHome):
    def _master(self):
        (self.home / "resumes").mkdir(parents=True, exist_ok=True)
        (self.home / "resumes" / "master.md").write_text(MASTER, encoding="utf-8")

    def _provider(self, draft=None, error=None):
        stub = unittest.mock.Mock()
        stub.tailor.side_effect = error
        if error is None:
            stub.tailor.return_value = draft
        return unittest.mock.patch("scout.smoke.load", return_value=stub), stub

    def test_the_default_model_is_free_and_says_so(self):
        self._master()
        ref = self.save()
        draft = MASTER.replace(
            "- Ran the Postgres upgrade", "- Ran the upgrade on Postgres"
        )
        patched, _ = self._provider(draft=draft)
        with patched, unittest.mock.patch("sys.stdout") as out:
            code = smoke.main([ref])
        self.assertEqual(code, 0)
        said = " ".join(str(call) for call in out.write.call_args_list)
        self.assertIn("costs nothing", said)

    def test_a_paid_model_says_what_it_expects_to_spend_first(self):
        self._master()
        ref = self.save()
        patched, _ = self._provider(draft=MASTER)
        with patched, unittest.mock.patch("sys.stdout") as out:
            smoke.main([ref, "--model", "anthropic/claude-sonnet-5"])
        said = " ".join(str(call) for call in out.write.call_args_list)
        self.assertIn("few cents", said)

    def test_a_refusal_is_the_result_rather_than_a_crash(self):
        self._master()
        ref = self.save()
        patched, _ = self._provider(error=ScoutError("no key"))
        with (
            patched,
            unittest.mock.patch("sys.stdout"),
            unittest.mock.patch("sys.stderr"),
        ):
            code = smoke.main([ref])
        # Non-zero, because the run did not produce a resume — but printed
        # rather than raised, since a caught invention is what this is for.
        self.assertEqual(code, 1)

    def test_the_model_can_be_named(self):
        self._master()
        ref = self.save()
        patched, stub = self._provider(draft=MASTER)
        with patched, unittest.mock.patch("sys.stdout"):
            smoke.main([ref, "--model", "google/gemma-4-31b-it:free"])
        self.assertEqual(stub.model, "google/gemma-4-31b-it:free")
