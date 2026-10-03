"""The paths the scenarios don't reach: the loop, the command line, and the
failures that aren't conflicts."""

import contextlib
import io
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent / "features"))

# Like the server: no git identity anywhere (see features/environment.py).
os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"

from support_repos import make_vault

from vault_sync import sync


class Repos(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="vault-sync-"))
        self.origin, self.laptop, self.worker = make_vault(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def agent_writes(self):
        path = self.worker / "Agents/Claude/Index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("memory\n")


class Loop(Repos):
    def test_keeps_syncing_until_stopped(self):
        sleeps = []

        def sleep(seconds):
            sleeps.append(seconds)
            raise KeyboardInterrupt

        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
            sync.run(self.worker, interval=60, once=False, sleep=sleep)
        self.assertEqual(sleeps, [60])

    def test_command_line_syncs_once(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(sync.main([str(self.worker), "--once"]), 0)
        self.assertIn("vault-sync: nothing to commit", out.getvalue())


class Failures(Repos):
    def run_once(self):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = sync.run(self.worker, interval=0, once=True)
        return code, err.getvalue()

    def test_a_pull_that_fails_without_a_conflict_is_reported(self):
        shutil.rmtree(self.origin)
        code, err = self.run_once()
        self.assertEqual(code, 1)
        self.assertIn("pull failed", err)

    def test_a_push_rejected_every_time_gives_up_and_says_so(self):
        hook = self.origin / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
        self.agent_writes()
        code, err = self.run_once()
        self.assertEqual(code, 1)
        self.assertIn("push still rejected after 3 attempts", err)

    def test_a_failing_git_command_says_which_and_why(self):
        with self.assertRaises(sync.SyncError) as caught:
            sync.git(self.worker, "rev-parse", "no-such-ref")
        self.assertIn("git rev-parse no-such-ref failed", str(caught.exception))

    def test_a_pushed_commit_is_reported_as_pushed(self):
        self.agent_writes()
        with mock.patch.object(sync, "print"):
            report = sync.sync(self.worker)
        self.assertTrue(report.pushed)
        self.assertIn("pushed", report.lines())


if __name__ == "__main__":
    unittest.main()
