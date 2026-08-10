from httpx_oauth.clients.facebook import FacebookOAuth2
from httpx_oauth.exceptions import GetIdEmailError
from httpx_oauth.oauth2 import OAuth2Error

from gary_api.identity.base import IdentityError, ProviderIdentity


class FacebookProvider:
    name = "facebook"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client = FacebookOAuth2(client_id, client_secret)

    async def authorization_url(self, redirect_uri: str, state: str) -> str:
        return await self._client.get_authorization_url(redirect_uri, state=state)

    async def identify(self, code: str, redirect_uri: str) -> ProviderIdentity:
        try:
            token = await self._client.get_access_token(code, redirect_uri)
            subject, email = await self._client.get_id_email(token["access_token"])
            profile = await self._client.get_profile(token["access_token"])
        except (OAuth2Error, GetIdEmailError) as error:
            raise IdentityError(f"facebook refused the sign in: {error}") from error

        # Facebook accounts can exist without an address at all — a phone
        # number is enough to register one — so this is a real path, not a
        # defensive one.
        if not email:
            raise IdentityError("facebook did not give an email address")

        return ProviderIdentity(
            subject=subject,
            email=email,
            display_name=profile.get("name") or email.split("@")[0],
        )
