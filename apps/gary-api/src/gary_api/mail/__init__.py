"""Outbound email.

Callers only ever see ``send``. Which provider carries the message is read
from the environment once, so swapping Resend for something else is a
config change, or at most a new module and one line in ``PROVIDERS``.

    MAIL_PROVIDER  console (default) or resend
    MAIL_FROM      the sender address
    RESEND_API_KEY required by the resend provider, and implies it
"""

import logging
import os
from collections.abc import Callable
from functools import cache

from gary_api.mail.base import MailError, Mailer, Message
from gary_api.mail.console import ConsoleMailer
from gary_api.mail.resend import ResendMailer

__all__ = [
    "MailError",
    "Mailer",
    "Message",
    "mailer",
    "report_configuration",
    "send",
    "sender",
]

logger = logging.getLogger(__name__)

# Resend's shared test sender. It needs no DNS, but it only delivers to the
# address that owns the Resend account — good enough to watch a reset link
# arrive, not good enough for real users. Set MAIL_FROM to an address on a
# verified domain before anyone but you signs up.
DEFAULT_SENDER = "gary <onboarding@resend.dev>"


def sender() -> str:
    return os.environ.get("MAIL_FROM", DEFAULT_SENDER)


def _build_console() -> Mailer:
    return ConsoleMailer()


def _build_resend() -> Mailer:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise MailError("the resend provider needs RESEND_API_KEY, which is not set")

    return ResendMailer(api_key=api_key, sender=sender())


PROVIDERS: dict[str, Callable[[], Mailer]] = {
    "console": _build_console,
    "resend": _build_resend,
}


def _selected() -> str:
    configured = os.environ.get("MAIL_PROVIDER")
    if configured:
        return configured

    # A key on its own says which provider is meant, so don't also demand
    # MAIL_PROVIDER and fall back to console while the key sits there unused.
    if os.environ.get("RESEND_API_KEY"):
        return "resend"

    return "console"


@cache
def mailer() -> Mailer:
    """The configured provider. Resolved once, then reused."""
    name = _selected()
    build = PROVIDERS.get(name)
    if build is None:
        known = ", ".join(sorted(PROVIDERS))
        raise MailError(f"MAIL_PROVIDER is {name!r}, which is not a provider. Try: {known}")

    return build()


def report_configuration() -> None:
    """Say at startup which provider will carry mail, and as whom.

    Without this the answer only shows up when someone needs a password
    reset, which is the worst moment to discover the key was never set.

    A broken mail config does not stop gary starting. Mail matters for
    password reset alone, and taking the service down over it would fail
    Fly's health check and block the deploy that fixes it.
    """
    try:
        provider = mailer()
    except MailError as error:
        logger.error("mail: nothing will send. %s", error)
        return

    logger.info("mail: sending through %s as %s", provider.name, sender())


async def send(message: Message) -> None:
    await mailer().send(message)
