from urllib.parse import quote

from gary_api.identity.base import IdentityError, ProviderIdentity

# The specs' stand-in for Google, Facebook and Apple.
#
# It reads the identity straight out of the code rather than holding state a
# scenario has to arrange first, so a spec says who is signing in at the
# moment it signs them in, and two scenarios can never leak into each other.
#
# The shape is subject|email|display name:
#
#     1234|ada@example.com|Ada Lovelace
#
# A code that will not parse is refused exactly as a real provider refusing
# an expired or replayed code would be, so the unhappy path is reachable too.


class FakeProvider:
    def __init__(self, name: str) -> None:
        self.name = name

    async def authorization_url(self, redirect_uri: str, state: str) -> str:
        return (
            f"https://fake-provider.invalid/{self.name}/authorize"
            f"?redirect_uri={quote(redirect_uri, safe='')}&state={quote(state, safe='')}"
        )

    async def identify(self, code: str, redirect_uri: str) -> ProviderIdentity:
        parts = code.split("|")
        if len(parts) != 3 or not all(part.strip() for part in parts):
            raise IdentityError(f"the fake provider cannot read {code!r} as an identity")

        subject, email, display_name = (part.strip() for part in parts)
        return ProviderIdentity(
            subject=subject, email=email, display_name=display_name
        )
