"""Sign in with Apple.

The wrapper the rest of gary never has to look at. Apple is the only one of
the three that is not a normal OAuth client, in two ways:

1. There is no client secret. There is a short-lived ES256 JWT you sign with
   a .p8 key from the developer portal, and Apple rejects one that expires
   more than six months out. Generated per request here rather than stored,
   because a stored one is a thing that works for months and then silently
   stops on a day nobody is deploying.

2. The name is not available from any endpoint. Apple includes it in the
   first callback and never again, so a caller that wants it must pass what
   it was given; afterwards the address is all there is.
"""

import time
from functools import cache
from typing import Any

import httpx
import jwt

from gary_api.identity.base import IdentityError, ProviderIdentity

AUTHORIZE_URL = "https://appleid.apple.com/auth/authorize"
TOKEN_URL = "https://appleid.apple.com/auth/token"
KEYS_URL = "https://appleid.apple.com/auth/keys"
ISSUER = "https://appleid.apple.com"

# Apple rejects anything beyond six months. Well inside it, since this is
# minted per request and only has to survive the round trip.
SECRET_LIFETIME = 600


@cache
def _jwk_client() -> "jwt.PyJWKClient":
    """Apple's signing keys, fetched once and cached across requests."""
    return jwt.PyJWKClient(KEYS_URL)


class AppleProvider:
    name = "apple"

    def __init__(
        self,
        client_id: str,
        team_id: str,
        key_id: str,
        private_key: str,
    ) -> None:
        self._client_id = client_id
        self._team_id = team_id
        self._key_id = key_id
        self._private_key = private_key

    async def authorization_url(self, redirect_uri: str, state: str) -> str:
        query = httpx.QueryParams(
            client_id=self._client_id,
            redirect_uri=redirect_uri,
            response_type="code",
            scope="name email",
            state=state,
            # Apple only returns name and email in the callback body, which
            # it will only POST. Without this the callback arrives empty.
            response_mode="form_post",
        )
        return f"{AUTHORIZE_URL}?{query}"

    def client_secret(self, now: float | None = None) -> str:
        issued = int(now if now is not None else time.time())
        return jwt.encode(
            {
                "iss": self._team_id,
                "iat": issued,
                "exp": issued + SECRET_LIFETIME,
                "aud": ISSUER,
                "sub": self._client_id,
            },
            self._private_key,
            algorithm="ES256",
            headers={"kid": self._key_id},
        )

    async def identify(
        self, code: str, redirect_uri: str, display_name: str | None = None
    ) -> ProviderIdentity:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self.client_secret(),
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )

        if response.status_code != httpx.codes.OK:
            raise IdentityError(
                f"apple refused the sign in: {response.status_code} {response.text}"
            )

        id_token = response.json().get("id_token")
        if not id_token:
            raise IdentityError("apple returned no id_token")

        claims = await self._verified_claims(id_token)
        subject = claims.get("sub")
        email = claims.get("email")
        if not subject or not email:
            raise IdentityError("apple's id_token carried no subject or email")

        # Hide My Email means this is often a relay address. It is a real
        # deliverable address and gary treats it as the person's own.
        return ProviderIdentity(
            subject=subject,
            email=email,
            display_name=display_name or email.split("@")[0],
        )

    async def _verified_claims(self, id_token: str) -> dict[str, Any]:
        """Check Apple's signature rather than trusting the token's contents.

        The token arrives over TLS from Apple, so this is belt and braces —
        but the whole account rests on `sub`, and verifying is a few lines.
        """
        try:
            signing_key = _jwk_client().get_signing_key_from_jwt(id_token)
            return jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._client_id,
                issuer=ISSUER,
            )
        except jwt.PyJWTError as error:
            raise IdentityError(f"apple's id_token did not verify: {error}") from error
