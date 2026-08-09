import logging

from gary_api.mail.base import Message

logger = logging.getLogger(__name__)


class ConsoleMailer:
    """Writes the message to the log instead of sending it.

    The default when no provider is configured, which is every developer
    machine and every spec run. It logs the body in full and on purpose: a
    password reset link nobody can read is the same as no reset at all, and
    the alternative is a seam that silently swallows mail.
    """

    name = "console"

    async def send(self, message: Message) -> None:
        logger.info(
            "mail: no provider configured, logging instead of sending.\n"
            "  to: %s\n  subject: %s\n%s",
            message.to,
            message.subject,
            message.text,
        )
