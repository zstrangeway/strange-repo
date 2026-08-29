"""A scratch SCOUT_HOME for a unit test, and a way to run the CLI in one."""

import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from scout import cli


class InAScratchHome(unittest.TestCase):
    """Each test gets its own directory, database and resumes/."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="scout-unit-"))
        self.previous = os.environ.get("SCOUT_HOME")
        os.environ["SCOUT_HOME"] = str(self.home)
        self.addCleanup(self._restore)

    def _restore(self):
        if self.previous is None:
            os.environ.pop("SCOUT_HOME", None)
        else:
            os.environ["SCOUT_HOME"] = self.previous
        shutil.rmtree(self.home, ignore_errors=True)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main([str(argument) for argument in argv])
        return code, out.getvalue() + err.getvalue()

    def save(self, title="Staff Engineer", company="Orrery"):
        code, output = self.run_cli(
            "save",
            "--text",
            f"{title} at {company}, working in Python.",
            "--title",
            title,
            "--company",
            company,
        )
        self.assertEqual(code, 0, output)
        return output.splitlines()[0].removeprefix("Saved ").strip()
