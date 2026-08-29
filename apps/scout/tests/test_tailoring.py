"""Tailoring, at the seams the CLI would contort to reach."""

import unittest

from support import InAScratchHome

from scout import db, grounding, tailoring
from scout.errors import ScoutError
from scout.providers.fake import FakeProvider

MASTER = """# Ada

## Skills

Python, Postgres

## Experience

### Wilding Labs — Senior Engineer

- Ran the Postgres upgrade
"""


class TheRefusal(unittest.TestCase):
    def test_one_invention_is_named_on_its_own(self):
        message = tailoring._refusal([grounding.Finding("skill", "Kubernetes")])
        self.assertEqual(
            message, 'Refused the draft: "Kubernetes" is not in the master resume.'
        )

    def test_every_invention_is_named_at_once(self):
        # Sending somebody back around the loop once per invented word is how
        # a tool gets abandoned.
        message = tailoring._refusal(
            [
                grounding.Finding("skill", "Kubernetes"),
                grounding.Finding("employer", "Initech"),
            ]
        )
        self.assertIn('"Kubernetes"', message)
        self.assertIn('"Initech"', message)


class Versions(InAScratchHome):
    def _master(self, text=MASTER):
        (self.home / "resumes").mkdir(parents=True, exist_ok=True)
        (self.home / "resumes" / "master.md").write_text(text, encoding="utf-8")

    def _draft(self, text):
        directory = self.home / ".scout"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "fake-draft.md").write_text(text, encoding="utf-8")

    def test_the_summary_is_stored_beside_the_file(self):
        self._master()
        ref = self.save()
        self._draft(
            MASTER.replace(
                "- Ran the Postgres upgrade", "- Ran the upgrade on Postgres"
            )
        )
        with db.connect() as connection:
            result = tailoring.tailor(connection, ref, FakeProvider())
            stored = connection.execute(
                "SELECT summary, path, version FROM resumes"
            ).fetchone()
        self.assertEqual(stored["version"], 1)
        self.assertEqual(stored["path"], str(result.path))
        self.assertIn("rewritten", stored["summary"])

    def test_a_refused_draft_leaves_no_row_and_no_file(self):
        self._master()
        ref = self.save()
        self._draft(MASTER.replace("Python, Postgres", "Python, Postgres, Kubernetes"))
        with db.connect() as connection, self.assertRaises(ScoutError):
            tailoring.tailor(connection, ref, FakeProvider())
        with db.connect() as connection:
            self.assertEqual(connection.execute("SELECT * FROM resumes").fetchall(), [])
        self.assertFalse((self.home / "resumes" / ref).exists())
