import os
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


def api_base_url() -> str:
    """Where this API answers, as a browser would reach it."""
    return os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")


# What the consent screen offers by default, so a spec that only needs
# "somebody" does not have to invent one.
FAKE_HINT = "1234|ada@example.com|Ada Lovelace"


class FakeProvider:
    def __init__(self, name: str) -> None:
        self.name = name

    async def authorization_url(self, redirect_uri: str, state: str) -> str:
        # Somewhere a browser can actually go. It used to be an invalid host,
        # which was fine for specs that only call the API and useless for the
        # end-to-end ones — signing in is a real navigation out and back, and
        # a provider you cannot navigate to cannot be exercised at all.
        return (
            f"{api_base_url()}/auth/fake/{self.name}/authorize"
            f"?redirect_uri={quote(redirect_uri, safe='')}&state={quote(state, safe='')}"
        )

    async def identify(
        self, code: str, redirect_uri: str, display_name: str | None = None
    ) -> ProviderIdentity:
        parts = code.split("|")
        if len(parts) != 3 or not all(part.strip() for part in parts):
            raise IdentityError(f"the fake provider cannot read {code!r} as an identity")

        subject, email, from_code = (part.strip() for part in parts)
        # Apple's name arrives alongside the code rather than in it, and wins
        # when a caller was given one — matching how the real provider works.
        return ProviderIdentity(
            subject=subject, email=email, display_name=display_name or from_code
        )
