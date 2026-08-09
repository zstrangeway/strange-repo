import unittest
from unittest.mock import patch

from gary_api.db import DEFAULT_URL, database_url


class DatabaseUrlTests(unittest.TestCase):
    def test_falls_back_when_unset(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(database_url(), DEFAULT_URL)

    def test_upgrades_postgres_scheme(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgres://u@h/db"}):
            self.assertEqual(database_url(), "postgresql+asyncpg://u@h/db")

    def test_upgrades_postgresql_scheme(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://u@h/db"}):
            self.assertEqual(database_url(), "postgresql+asyncpg://u@h/db")

    def test_leaves_an_async_url_alone(self):
        url = "postgresql+asyncpg://u@h/db"
        with patch.dict("os.environ", {"DATABASE_URL": url}):
            self.assertEqual(database_url(), url)


if __name__ == "__main__":
    unittest.main()
