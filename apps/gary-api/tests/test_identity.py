"""The real providers, which the Gherkin specs deliberately never reach.

Those specs run against the fake, because what they are about is what gary
does with an answer rather than whether Google can authenticate people. That
leaves the three shipped implementations untested, and they are exactly where
a provider's quirks live — so they are covered here instead, at the seam
where gary talks to them.
"""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from httpx_oauth.oauth2 import OAuth2Error

from gary_api import identity
from gary_api.identity.apple import AppleProvider
from gary_api.identity.base import IdentityError
from gary_api.identity.facebook import FacebookProvider
from gary_api.identity.google import GoogleProvider


def run(coroutine):
    return asyncio.run(coroutine)


def ec_key() -> str:
    """A throwaway P-256 key, the shape Apple hands out as a .p8."""
    return (
        ec.generate_private_key(ec.SECP256R1())
        .private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        .decode()
    )


class RegistryTests(unittest.TestCase):
    def setUp(self):
        identity.provider.cache_clear()
        self.addCleanup(identity.provider.cache_clear)

    def test_faking_serves_every_configured_name(self):
        with patch.dict(os.environ, {"IDENTITY_FAKE": "1"}):
            self.assertEqual(identity.provider("google").name, "google")

    def test_a_name_that_is_not_offered_is_refused(self):
        with patch.dict(os.environ, {"IDENTITY_PROVIDERS": "google"}):
            with self.assertRaises(IdentityError) as refused:
                identity.provider("myspace")

        self.assertIn("google", str(refused.exception))

    def test_a_provider_without_credentials_says_which_are_missing(self):
        env = {"IDENTITY_FAKE": "0", "GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}
        with patch.dict(os.environ, env):
            with self.assertRaises(IdentityError) as refused:
                identity.provider("google")

        self.assertIn("GOOGLE_CLIENT_ID", str(refused.exception))

    def test_each_provider_builds_when_its_credentials_are_there(self):
        env = {
            "IDENTITY_FAKE": "0",
            "GOOGLE_CLIENT_ID": "id", "GOOGLE_CLIENT_SECRET": "secret",
            "FACEBOOK_CLIENT_ID": "id", "FACEBOOK_CLIENT_SECRET": "secret",
            "APPLE_CLIENT_ID": "id", "APPLE_TEAM_ID": "team",
            "APPLE_KEY_ID": "key", "APPLE_PRIVATE_KEY": ec_key().replace("\n", "\\n"),
        }
        with patch.dict(os.environ, env):
            for name in ("google", "facebook", "apple"):
                identity.provider.cache_clear()
                self.assertEqual(identity.provider(name).name, name)

    def test_a_name_with_no_implementation_is_refused(self):
        env = {"IDENTITY_FAKE": "0", "IDENTITY_PROVIDERS": "myspace"}
        with patch.dict(os.environ, env):
            with self.assertRaises(IdentityError):
                identity.provider("myspace")

    def test_configured_can_be_narrowed(self):
        with patch.dict(os.environ, {"IDENTITY_PROVIDERS": "google, apple"}):
            self.assertEqual(identity.configured(), ["google", "apple"])


class ReportingTests(unittest.TestCase):
    """A provider missing its credentials must be loud at startup.

    The alternative is a button that cannot work, discovered by a user.
    """

    def setUp(self):
        identity.provider.cache_clear()
        self.addCleanup(identity.provider.cache_clear)

    def test_faking_is_reported_rather_than_passed_over(self):
        with patch.dict(os.environ, {"IDENTITY_FAKE": "1"}):
            with patch.object(identity.logger, "warning") as warned:
                identity.report_configuration()

        warned.assert_called_once()

    def test_a_misconfigured_provider_is_reported_and_the_rest_carry_on(self):
        env = {
            "IDENTITY_FAKE": "0",
            "IDENTITY_PROVIDERS": "google,facebook",
            "GOOGLE_CLIENT_ID": "id", "GOOGLE_CLIENT_SECRET": "secret",
            "FACEBOOK_CLIENT_ID": "", "FACEBOOK_CLIENT_SECRET": "",
        }
        with patch.dict(os.environ, env):
            with patch.object(identity.logger, "error") as failed:
                with patch.object(identity.logger, "info") as fine:
                    identity.report_configuration()

        self.assertEqual(failed.call_count, 1)
        self.assertEqual(fine.call_count, 1)


class GoogleTests(unittest.TestCase):
    def setUp(self):
        self.provider = GoogleProvider("id", "secret")

    def _client(self, **overrides):
        client = self.provider._client
        client.get_access_token = AsyncMock(return_value={"access_token": "t"})
        client.get_id_email = AsyncMock(return_value=("1234", "ada@example.com"))
        client.get_profile = AsyncMock(
            return_value={"names": [{"displayName": "Ada Lovelace"}]}
        )
        for name, value in overrides.items():
            setattr(client, name, value)
        return client

    def test_identifies_someone(self):
        self._client()
        who = run(self.provider.identify("code", "http://back"))

        self.assertEqual(who.subject, "1234")
        self.assertEqual(who.display_name, "Ada Lovelace")

    def test_falls_back_to_the_local_part_when_there_is_no_name(self):
        self._client(get_profile=AsyncMock(return_value={"names": []}))
        self.assertEqual(run(self.provider.identify("c", "u")).display_name, "ada")

    def test_a_names_entry_with_no_display_name_is_passed_over(self):
        # Google returns the list with entries that carry no displayName, so
        # the loop has to run out rather than take the first entry blindly.
        self._client(get_profile=AsyncMock(return_value={"names": [{}, {}]}))
        self.assertEqual(run(self.provider.identify("c", "u")).display_name, "ada")

    def test_a_profile_with_no_names_key_at_all(self):
        self._client(get_profile=AsyncMock(return_value={}))
        self.assertEqual(run(self.provider.identify("c", "u")).display_name, "ada")

    def test_a_declined_email_scope_is_refused(self):
        self._client(get_id_email=AsyncMock(return_value=("1234", None)))
        with self.assertRaises(IdentityError):
            run(self.provider.identify("c", "u"))

    def test_a_refusal_from_google_is_an_identity_error(self):
        self._client(get_access_token=AsyncMock(side_effect=OAuth2Error("nope")))
        with self.assertRaises(IdentityError):
            run(self.provider.identify("c", "u"))

    def test_offers_somewhere_to_send_people(self):
        url = run(self.provider.authorization_url("http://back", "state"))
        self.assertIn("accounts.google.com", url)


class FacebookTests(unittest.TestCase):
    def setUp(self):
        self.provider = FacebookProvider("id", "secret")

    def _client(self, **overrides):
        client = self.provider._client
        client.get_access_token = AsyncMock(return_value={"access_token": "t"})
        client.get_id_email = AsyncMock(return_value=("9876", "ada@example.com"))
        client.get_profile = AsyncMock(return_value={"name": "Ada Lovelace"})
        for name, value in overrides.items():
            setattr(client, name, value)
        return client

    def test_identifies_someone(self):
        self._client()
        self.assertEqual(run(self.provider.identify("c", "u")).subject, "9876")

    def test_an_account_with_no_address_is_refused(self):
        # Facebook accounts can be registered with a phone number alone, so
        # this is a real path rather than a defensive one.
        self._client(get_id_email=AsyncMock(return_value=("9876", None)))
        with self.assertRaises(IdentityError):
            run(self.provider.identify("c", "u"))

    def test_falls_back_when_the_profile_carries_no_name(self):
        self._client(get_profile=AsyncMock(return_value={}))
        self.assertEqual(run(self.provider.identify("c", "u")).display_name, "ada")

    def test_a_refusal_is_an_identity_error(self):
        self._client(get_access_token=AsyncMock(side_effect=OAuth2Error("nope")))
        with self.assertRaises(IdentityError):
            run(self.provider.identify("c", "u"))

    def test_offers_somewhere_to_send_people(self):
        url = run(self.provider.authorization_url("http://back", "state"))
        self.assertIn("facebook.com", url)


class AppleTests(unittest.TestCase):
    def setUp(self):
        self.key = ec_key()
        self.provider = AppleProvider("app.id", "TEAM", "KEY", self.key)

    def test_the_client_secret_is_signed_and_short_lived(self):
        secret = self.provider.client_secret(now=1_000_000)
        claims = jwt.decode(secret, options={"verify_signature": False},
                            audience="https://appleid.apple.com")

        self.assertEqual(claims["iss"], "TEAM")
        self.assertEqual(claims["sub"], "app.id")
        # Apple rejects anything more than six months out. Minted per
        # request, so it only has to outlive the round trip.
        self.assertLess(claims["exp"] - claims["iat"], 15_777_000)
        self.assertEqual(jwt.get_unverified_header(secret)["kid"], "KEY")

    def test_the_authorization_url_asks_for_a_form_post(self):
        # Apple only returns the name in a POSTed callback, and only once.
        url = run(self.provider.authorization_url("http://back", "state"))
        self.assertIn("response_mode=form_post", url)
        self.assertIn("appleid.apple.com", url)

    def _token_response(self, status=200, body=None):
        response = unittest.mock.Mock()
        response.status_code = status
        response.text = "detail"
        response.json.return_value = body if body is not None else {"id_token": "tok"}
        return response

    def _posting(self, response):
        client = AsyncMock()
        client.post = AsyncMock(return_value=response)
        context = AsyncMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)
        return patch("gary_api.identity.apple.httpx.AsyncClient", return_value=context)

    def test_identifies_someone_and_prefers_the_name_it_was_handed(self):
        claims = {"sub": "001.abc", "email": "l9x2@privaterelay.appleid.com"}
        with self._posting(self._token_response()):
            with patch.object(AppleProvider, "_verified_claims",
                              AsyncMock(return_value=claims)):
                who = run(self.provider.identify("c", "u", "Ada Lovelace"))

        self.assertEqual(who.subject, "001.abc")
        self.assertEqual(who.display_name, "Ada Lovelace")

    def test_without_a_name_it_falls_back_to_the_address(self):
        claims = {"sub": "001.abc", "email": "ada@example.com"}
        with self._posting(self._token_response()):
            with patch.object(AppleProvider, "_verified_claims",
                              AsyncMock(return_value=claims)):
                who = run(self.provider.identify("c", "u"))

        self.assertEqual(who.display_name, "ada")

    def test_a_refusal_from_apple_is_an_identity_error(self):
        with self._posting(self._token_response(status=400)):
            with self.assertRaises(IdentityError):
                run(self.provider.identify("c", "u"))

    def test_a_response_with_no_id_token_is_refused(self):
        with self._posting(self._token_response(body={})):
            with self.assertRaises(IdentityError):
                run(self.provider.identify("c", "u"))

    def test_claims_without_a_subject_are_refused(self):
        with self._posting(self._token_response()):
            with patch.object(AppleProvider, "_verified_claims",
                              AsyncMock(return_value={"email": "a@b.c"})):
                with self.assertRaises(IdentityError):
                    run(self.provider.identify("c", "u"))

    def test_the_key_client_is_built_once_and_reused(self):
        # Cached because it is asked for on every Apple sign-in, and each
        # miss is a round trip to Apple for keys that rarely change.
        from gary_api.identity.apple import _jwk_client

        _jwk_client.cache_clear()
        self.addCleanup(_jwk_client.cache_clear)
        self.assertIs(_jwk_client(), _jwk_client())

    def test_an_id_token_that_does_not_verify_is_refused(self):
        with patch("gary_api.identity.apple._jwk_client") as keys:
            keys.return_value.get_signing_key_from_jwt.side_effect = jwt.PyJWTError("x")
            with self.assertRaises(IdentityError):
                run(self.provider._verified_claims("tok"))

    def test_a_verified_id_token_yields_its_claims(self):
        with patch("gary_api.identity.apple._jwk_client") as keys:
            keys.return_value.get_signing_key_from_jwt.return_value.key = "k"
            with patch("gary_api.identity.apple.jwt.decode",
                       return_value={"sub": "001"}) as decoded:
                claims = run(self.provider._verified_claims("tok"))

        self.assertEqual(claims["sub"], "001")
        decoded.assert_called_once()


if __name__ == "__main__":
    unittest.main()
