import logging
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from gary_api.app import app


class LifespanTests(unittest.TestCase):
    def test_reports_the_mail_configuration_on_startup(self):
        # Entering the client is what runs the lifespan; constructing one on
        # its own does not.
        with patch("gary_api.mail.report_configuration") as report:
            with TestClient(app):
                pass

        report.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()


class LoggingTests(unittest.TestCase):
    """Regression: gary-api's own log records went nowhere under uvicorn.

    uvicorn configures its own loggers and leaves the root one alone, so
    anything below WARNING was dropped — including the reset link the console
    mail provider exists to print. Password reset was unusable locally and
    silent about why.
    """

    def test_startup_makes_the_apps_own_info_records_visible(self):
        root = logging.getLogger()
        handlers, level = root.handlers[:], root.level
        self.addCleanup(lambda: (root.handlers.__setitem__(slice(None), handlers),
                                 root.setLevel(level)))

        # The state uvicorn leaves behind: no handler on the root logger.
        root.handlers.clear()
        root.setLevel(logging.WARNING)

        with TestClient(app):
            pass

        self.assertTrue(root.handlers, "nothing would print the app's records")
        self.assertLessEqual(
            logging.getLogger("gary_api.mail.console").getEffectiveLevel(),
            logging.INFO,
            "INFO records, including the reset link, would still be dropped",
        )
