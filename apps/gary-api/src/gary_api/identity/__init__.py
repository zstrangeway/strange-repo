"""Who someone is, according to Google, Facebook or Apple.

gary authenticates nobody. Each provider does that and gary trusts the
result, which is why there is no password anywhere in this package.

Callers only ever see ``provider(name)``. Which implementations are live is
read from the environment once, the same arrangement as ``mail``:

    IDENTITY_PROVIDERS   comma-separated, default "google,facebook,apple"
    IDENTITY_FAKE        set to 1 to serve every name with the spec double

    GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
    FACEBOOK_CLIENT_ID / FACEBOOK_CLIENT_SECRET
    APPLE_CLIENT_ID / APPLE_TEAM_ID / APPLE_KEY_ID / APPLE_PRIVATE_KEY
"""

import os
from collections.abc import Callable
from functools import cache

from gary_api import logs
from gary_api.identity.apple import AppleProvider
from gary_api.identity.base import IdentityError, Provider, ProviderIdentity
from gary_api.identity.facebook import FacebookProvider
from gary_api.identity.fake import FakeProvider
from gary_api.identity.google import GoogleProvider

__all__ = [
    "IdentityError",
    "Provider",
    "ProviderIdentity",
    "configured",
    "provider",
    "report_configuration",
]

logger = logs.get_logger(__name__)

DEFAULT_PROVIDERS = "google,facebook,apple"


def _require(*names: str) -> list[str]:
    values = [os.environ.get(name, "") for name in names]
    missing = [name for name, value in zip(names, values) if not value]
    if missing:
        raise IdentityError(f"missing {', '.join(missing)}")

    return values


def _build_google() -> Provider:
    client_id, secret = _require("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET")
    return GoogleProvider(client_id, secret)


def _build_facebook() -> Provider:
    client_id, secret = _require("FACEBOOK_CLIENT_ID", "FACEBOOK_CLIENT_SECRET")
    return FacebookProvider(client_id, secret)


def _build_apple() -> Provider:
    client_id, team_id, key_id, private_key = _require(
        "APPLE_CLIENT_ID", "APPLE_TEAM_ID", "APPLE_KEY_ID", "APPLE_PRIVATE_KEY"
    )
    # The .p8 arrives as one line through Fly's secrets, and PEM needs its
    # newlines back or the key will not parse.
    return AppleProvider(client_id, team_id, key_id, private_key.replace("\\n", "\n"))


BUILDERS: dict[str, Callable[[], Provider]] = {
    "google": _build_google,
    "facebook": _build_facebook,
    "apple": _build_apple,
}


def _faking() -> bool:
    return os.environ.get("IDENTITY_FAKE") == "1"


def configured() -> list[str]:
    """The provider names this deployment offers, in the order to show them."""
    names = os.environ.get("IDENTITY_PROVIDERS", DEFAULT_PROVIDERS)
    return [name.strip() for name in names.split(",") if name.strip()]


@cache
def provider(name: str) -> Provider:
    """The named provider. Built once, then reused."""
    if name not in configured():
        known = ", ".join(configured())
        raise IdentityError(f"{name!r} is not a provider here. Try: {known}")

    if _faking():
        return FakeProvider(name)

    build = BUILDERS.get(name)
    if build is None:
        raise IdentityError(f"{name!r} has no implementation")

    return build()


def report_configuration() -> None:
    """Say at startup which providers will work, and which will not.

    A provider missing its credentials is not a reason to refuse to start —
    the other two still sign people in — but it must not be discovered by a
    user clicking the button either.
    """
    if _faking():
        logger.warning("identity.faking", providers=configured())
        return

    for name in configured():
        try:
            provider(name)
        except IdentityError as error:
            logger.error("identity.misconfigured", provider=name, reason=str(error))
        else:
            logger.info("identity.configured", provider=name)
