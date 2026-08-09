from gary_api import logs
from gary_api.mail.base import Message

logger = logs.get_logger(__name__)


class ConsoleMailer:
    """Writes the message to the log instead of sending it.

    The default when no provider is configured, which is every developer
    machine and every spec run. It logs the body in full and on purpose: a
    password reset link nobody can read is the same as no reset at all, and
    the alternative is a seam that silently swallows mail.

    The body is a field rather than part of the message, so the end-to-end
    suite can pull the reset link out of one JSON object instead of parsing
    several lines of prose. Set LOG_FORMAT=text to read it by eye.
    """

    name = "console"

    async def send(self, message: Message) -> None:
        logger.info(
            "mail.logged",
            to=message.to,
            subject=message.subject,
            body=message.text,
        )
