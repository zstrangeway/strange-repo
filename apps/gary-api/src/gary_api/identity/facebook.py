from typing import Any

from httpx_oauth.clients.facebook import PROFILE_ENDPOINT, FacebookOAuth2
from httpx_oauth.exceptions import GetProfileError
from httpx_oauth.oauth2 import OAuth2Error

from gary_api.identity.base import IdentityError, ProviderIdentity

# httpx-oauth asks the graph for id and email only, so the name it then
# reads off the profile was never in the response. We ask for all three.
PROFILE_FIELDS = "id,name,email"


class FacebookProvider:
    name = "facebook"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client = FacebookOAuth2(client_id, client_secret)

    async def authorization_url(self, redirect_uri: str, state: str) -> str:
        return await self._client.get_authorization_url(redirect_uri, state=state)

    async def identify(self, code: str, redirect_uri: str) -> ProviderIdentity:
        try:
            token = await self._client.get_access_token(code, redirect_uri)
            profile = await self._profile(token["access_token"])
        except (OAuth2Error, GetProfileError) as error:
            raise IdentityError(f"facebook refused the sign in: {error}") from error

        email = profile.get("email")
        # Facebook accounts can exist without an address at all — a phone
        # number is enough to register one — so this is a real path, not a
        # defensive one.
        if not email:
            raise IdentityError("facebook did not give an email address")

        return ProviderIdentity(
            subject=profile["id"],
            email=email,
            display_name=profile.get("name") or email.split("@")[0],
        )

    async def _profile(self, token: str) -> dict[str, Any]:
        async with self._client.get_httpx_client() as client:
            response = await client.get(
                PROFILE_ENDPOINT,
                params={"fields": PROFILE_FIELDS, "access_token": token},
            )

            if response.status_code >= 400:
                raise GetProfileError(response=response)

            return dict(response.json())
