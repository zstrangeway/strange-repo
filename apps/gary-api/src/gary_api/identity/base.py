from dataclasses import dataclass
from typing import Protocol


class IdentityError(Exception):
    """A provider could not, or would not, say who someone is."""


@dataclass(frozen=True)
class ProviderIdentity:
    """What a provider tells gary about the person who just signed in.

    ``subject`` is the provider's own identifier and the only field gary keys
    on. ``email`` and ``display_name`` are taken on trust for display, and
    nothing is granted on the strength of either.
    """

    subject: str
    email: str
    display_name: str


class Provider(Protocol):
    name: str

    async def authorization_url(self, redirect_uri: str, state: str) -> str:
        """Where to send someone so this provider can authenticate them."""
        ...

    async def identify(self, code: str, redirect_uri: str) -> ProviderIdentity:
        """Redeem the code the provider handed back, and say who it belongs to.

        Raises IdentityError when the provider refuses, or answers with
        something gary cannot make an identity out of.
        """
        ...
