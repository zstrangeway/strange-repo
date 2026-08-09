from dataclasses import dataclass
from typing import Protocol


class MailError(RuntimeError):
    """A message could not be handed to a provider.

    Covers both a provider that refused a message and one that could not be
    built because its configuration is missing.
    """


@dataclass(frozen=True)
class Message:
    to: str
    subject: str
    text: str


class Mailer(Protocol):
    """The whole surface a provider has to implement.

    Adding a provider is: write one of these, register it in PROVIDERS.
    Nothing that sends mail knows which one it got, so swapping providers
    never reaches past this package.
    """

    name: str

    async def send(self, message: Message) -> None: ...
