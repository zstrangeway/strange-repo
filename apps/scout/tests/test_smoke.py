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

    def test_it_says_what_it_is_about_to_spend_before_it_spends_it(self):
        self._master()
        ref = self.save()
        draft = MASTER.replace(
            "- Ran the Postgres upgrade", "- Ran the upgrade on Postgres"
        )
        with unittest.mock.patch("scout.smoke.AnthropicProvider") as provider:
            provider.return_value.tailor.return_value = draft
            with unittest.mock.patch("sys.stdout") as out:
                code = smoke.main([ref])
        self.assertEqual(code, 0)
        said = " ".join(str(call) for call in out.write.call_args_list)
        self.assertIn("About to call", said)

    def test_a_refusal_is_the_result_rather_than_a_crash(self):
        self._master()
        ref = self.save()
        with unittest.mock.patch("scout.smoke.AnthropicProvider") as provider:
            provider.return_value.tailor.side_effect = ScoutError("no key")
            with unittest.mock.patch("sys.stdout"), unittest.mock.patch("sys.stderr"):
                code = smoke.main([ref])
        # Non-zero, because the run did not produce a resume — but printed
        # rather than raised, since a caught invention is what this is for.
        self.assertEqual(code, 1)

    def test_the_model_can_be_named(self):
        self._master()
        ref = self.save()
        with unittest.mock.patch("scout.smoke.AnthropicProvider") as provider:
            provider.return_value.tailor.return_value = MASTER
            with unittest.mock.patch("sys.stdout"):
                smoke.main([ref, "--model", "claude-opus-5"])
        provider.assert_called_once_with(model="claude-opus-5")
