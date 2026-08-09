import asyncio
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from gary_api import seed
from gary_api.db import database_url
from gary_api.passwords import verify_password


class IsLocalTests(unittest.TestCase):
    def test_accepts_loopback(self):
        self.assertTrue(seed.is_local("postgresql+asyncpg://postgres@127.0.0.1:5432/db"))

    def test_accepts_localhost(self):
        self.assertTrue(seed.is_local("postgresql+asyncpg://postgres@localhost/db"))

    def test_accepts_a_compose_style_host(self):
        self.assertTrue(seed.is_local("postgresql+asyncpg://postgres@db:5432/gary"))

    def test_rejects_a_hosted_database(self):
        self.assertFalse(
            seed.is_local("postgresql+asyncpg://u:p@gary-db.flympg.net:5432/gary")
        )


class SeedTests(unittest.TestCase):
    """Against the real database, because the whole job is what it wrote."""

    def setUp(self):
        # A fresh engine, pooling off: each asyncio.run is a new event loop,
        # and a pooled connection from the previous one cannot be reused.
        self.engine = create_async_engine(database_url(), poolclass=NullPool)
        patcher = patch.object(seed, "engine", self.engine)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(lambda: self._run(self.engine.dispose()))
        self._sql("TRUNCATE users CASCADE")

    def _run(self, coroutine):
        return asyncio.run(coroutine)

    def _sql(self, statement):
        async def run():
            async with self.engine.begin() as connection:
                result = await connection.execute(text(statement))
                return result.fetchall() if result.returns_rows else []

        return asyncio.run(run())

    def test_creates_every_account(self):
        lines = self._run(seed.seed())

        self.assertEqual(len(lines), len(seed.ACCOUNTS))
        self.assertTrue(all("created" in line for line in lines))

        rows = self._sql("SELECT email, display_name, password_hash FROM users")
        self.assertEqual(
            sorted(row[0] for row in rows), sorted(e for e, _ in seed.ACCOUNTS)
        )
        for _, _, password_hash in rows:
            self.assertTrue(verify_password(password_hash, seed.PASSWORD))

    def test_rerunning_resets_rather_than_failing(self):
        self._run(seed.seed())
        self._sql("UPDATE users SET display_name = 'Drifted'")

        lines = self._run(seed.seed())

        self.assertTrue(all("reset" in line for line in lines))
        # The point of re-running: a mangled local database comes back.
        names = [row[0] for row in self._sql("SELECT display_name FROM users")]
        self.assertNotIn("Drifted", names)
        self.assertEqual(len(names), len(seed.ACCOUNTS))


class MainTests(unittest.TestCase):
    def test_refuses_a_database_that_is_not_local(self):
        with patch.object(seed, "database_url", return_value="postgresql://u@prod/db"):
            # A plain callable, not the async original: asyncio.run never
            # gets to await it, and an AsyncMock would warn about that.
            with patch.object(seed, "seed", new=MagicMock()) as never:
                self.assertEqual(seed.main(), 1)

        # The point of the guard is that nothing ran.
        never.assert_not_called()

    def test_reports_every_account_it_touched(self):
        lines = ["  created  ada@example.com  (Ada Lovelace)"]

        with patch.object(seed, "database_url", return_value="postgresql://u@localhost/db"):
            with patch.object(seed.asyncio, "run", return_value=lines):
                with patch.object(seed, "seed", new=MagicMock()):
                    with patch("builtins.print") as printed:
                        self.assertEqual(seed.main(), 0)

        said = " ".join(str(call.args[0]) for call in printed.call_args_list if call.args)
        self.assertIn("ada@example.com", said)
        # A seed that does not say the password is a seed you cannot use.
        self.assertIn(seed.PASSWORD, said)


if __name__ == "__main__":
    unittest.main()
