"""A synced creed in a scratch directory, for tests that need real rows.

The unit tests cover what the specs do not reach: the command line's every
subcommand and refusal, each tool on the server, every branch of the
renderers, and shapes of the export the fixture does not happen to contain.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "features"))

from support.export_site import ExportSite

from creed import db, sync


class CreedTestCase(unittest.TestCase):
    """Each test gets its own database and its own export site."""

    sync_on_setup = True

    def setUp(self) -> None:
        self._saved = {
            name: os.environ.get(name) for name in ("CREED_HOME", "CREED_EXPORT_BASE")
        }
        self.home = Path(tempfile.mkdtemp(prefix="creed-test-"))
        os.environ["CREED_HOME"] = str(self.home)
        self.site = ExportSite()
        os.environ["CREED_EXPORT_BASE"] = self.site.base_url
        if self.sync_on_setup:
            result = sync.sync()
            self.assertIsNone(result.failed, result.failed)

    def tearDown(self) -> None:
        self.site.close()
        shutil.rmtree(self.home, ignore_errors=True)
        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def connection(self):
        return db.session()
