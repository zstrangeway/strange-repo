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
