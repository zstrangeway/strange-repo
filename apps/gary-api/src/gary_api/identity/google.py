from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.exceptions import GetIdEmailError
from httpx_oauth.oauth2 import OAuth2Error

from gary_api.identity.base import IdentityError, ProviderIdentity


class GoogleProvider:
    name = "google"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client = GoogleOAuth2(client_id, client_secret)

    async def authorization_url(self, redirect_uri: str, state: str) -> str:
        return await self._client.get_authorization_url(redirect_uri, state=state)

    async def identify(self, code: str, redirect_uri: str) -> ProviderIdentity:
        try:
            token = await self._client.get_access_token(code, redirect_uri)
            subject, email = await self._client.get_id_email(token["access_token"])
            profile = await self._client.get_profile(token["access_token"])
        except (OAuth2Error, GetIdEmailError) as error:
            raise IdentityError(f"google refused the sign in: {error}") from error

        if not email:
            # Google will withhold the address if the scope was declined, and
            # gary has nothing to show on a profile page without one.
            raise IdentityError("google did not give an email address")

        return ProviderIdentity(
            subject=subject, email=email, display_name=_name_from(profile, email)
        )


def _name_from(profile: dict, email: str) -> str:
    """Google's People API nests the name and may omit it entirely."""
    for entry in profile.get("names") or []:
        display = entry.get("displayName")
        if display:
            return display

    return email.split("@")[0]
