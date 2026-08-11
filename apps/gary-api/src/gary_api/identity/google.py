from typing import Any

from httpx_oauth.clients.google import PROFILE_ENDPOINT, GoogleOAuth2
from httpx_oauth.exceptions import GetProfileError
from httpx_oauth.oauth2 import OAuth2Error

from gary_api.identity.base import IdentityError, ProviderIdentity

# What we ask the People API for. httpx-oauth's own get_profile asks for
# emailAddresses alone, so a name could never come back through it — which
# is why we call People ourselves rather than using it.
PERSON_FIELDS = "names,emailAddresses"


class GoogleProvider:
    name = "google"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client = GoogleOAuth2(client_id, client_secret)

    async def authorization_url(self, redirect_uri: str, state: str) -> str:
        return await self._client.get_authorization_url(redirect_uri, state=state)

    async def identify(self, code: str, redirect_uri: str) -> ProviderIdentity:
        try:
            token = await self._client.get_access_token(code, redirect_uri)
            profile = await self._profile(token["access_token"])
        except (OAuth2Error, GetProfileError) as error:
            raise IdentityError(f"google refused the sign in: {error}") from error

        email = _email_from(profile)
        if not email:
            # Google will withhold the address if the scope was declined, and
            # gary has nothing to show on a profile page without one.
            raise IdentityError("google did not give an email address")

        return ProviderIdentity(
            subject=profile["resourceName"],
            email=email,
            display_name=_name_from(profile, email),
        )

    async def _profile(self, token: str) -> dict[str, Any]:
        """The People record, in one call, carrying everything gary needs.

        A 4xx here is most often the People API not being enabled on the
        Cloud project: the token exchange succeeds and then this refuses,
        which is worth knowing when a sign-in fails with good credentials.
        """
        async with self._client.get_httpx_client() as client:
            response = await client.get(
                PROFILE_ENDPOINT,
                params={"personFields": PERSON_FIELDS},
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code >= 400:
                raise GetProfileError(response=response)

            return dict(response.json())


def _email_from(profile: dict[str, Any]) -> str | None:
    """The address Google calls primary, or the only one it gave."""
    addresses = profile.get("emailAddresses") or []
    for entry in addresses:
        if entry.get("metadata", {}).get("primary"):
            return entry.get("value")

    return addresses[0].get("value") if addresses else None


def _name_from(profile: dict[str, Any], email: str) -> str:
    """Google's People API nests the name and may omit it entirely."""
    for entry in profile.get("names") or []:
        display = entry.get("displayName")
        if display:
            return display

    return email.split("@")[0]
