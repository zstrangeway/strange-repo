"""The two paths in auth.py that the Gherkin specs cannot reach.

One needs a provider that is configured but broken; the other needs two
requests racing each other. Both are real, and neither is arrangeable from
outside the app.
"""

import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from gary_api import auth, identity
from gary_api.identity.base import IdentityError, ProviderIdentity


def run(coroutine):
    return asyncio.run(coroutine)


class ListProvidersTests(unittest.TestCase):
    def test_a_provider_that_cannot_be_built_is_left_out_rather_than_fatal(self):
        """One missing credential must not take out the other two.

        A button that cannot work is worse than no button, and an endpoint
        that 500s takes away the ways in that do work.
        """
        working = Mock()
        working.authorization_url = AsyncMock(return_value="https://example.test/go")

        def build(name):
            if name == "facebook":
                raise IdentityError("missing FACEBOOK_CLIENT_ID")
            return working

        with patch.object(identity, "configured",
                          return_value=["google", "facebook", "apple"]):
            with patch.object(identity, "provider", side_effect=build):
                with patch.object(auth.logger, "error") as complained:
                    offered = run(auth.list_providers("http://back", "state"))

        self.assertEqual([row.name for row in offered], ["google", "apple"])
        complained.assert_called_once()


class ConnectIdentityTests(unittest.TestCase):
    def test_losing_the_race_to_connect_reads_as_already_connected(self):
        """Two requests connecting the same identity at once.

        Both pass the "is it taken?" check; the unique constraint is what
        actually decides, and the loser has to say the same thing the check
        would have said rather than a 500.
        """
        request = auth.SignInRequest(
            provider="facebook", code="c", redirect_uri="http://back"
        )
        user = Mock(id=uuid.uuid4())
        database = AsyncMock()
        database.add = Mock()
        database.commit = AsyncMock(
            side_effect=IntegrityError("insert", {}, Exception("duplicate"))
        )

        who = ProviderIdentity(subject="9876", email="ada@example.com",
                               display_name="Ada")
        with patch.object(auth, "_identify", AsyncMock(return_value=who)):
            with patch.object(auth, "_find", AsyncMock(return_value=None)):
                with self.assertRaises(HTTPException) as refused:
                    run(auth.connect_identity(request, database, user))

        self.assertEqual(refused.exception.status_code, 409)
        self.assertIn("already connected", refused.exception.detail)
        database.rollback.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
