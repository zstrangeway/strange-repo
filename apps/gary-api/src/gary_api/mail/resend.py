import httpx

from gary_api.mail.base import MailError, Message

API_URL = "https://api.resend.com/emails"
TIMEOUT_SECONDS = 10.0


class ResendMailer:
    """Sends through Resend's HTTP API.

    HTTP rather than SMTP because Fly blocks outbound port 25 and 587 is
    unreliable there, so an SMTP provider would work locally and silently
    time out in production.
    """

    name = "resend"

    def __init__(self, api_key: str, sender: str) -> None:
        self._api_key = api_key
        self._sender = sender

    async def send(self, message: Message) -> None:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.post(
                    API_URL,
                    headers={"authorization": f"Bearer {self._api_key}"},
                    json={
                        "from": self._sender,
                        "to": [message.to],
                        "subject": message.subject,
                        "text": message.text,
                    },
                )
        except httpx.HTTPError as error:
            raise MailError(f"resend was unreachable: {error}") from error

        if response.is_error:
            # The body carries the reason and the status does not: an
            # unverified sender and a revoked key are both 403, and the two
            # need very different fixing.
            raise MailError(
                f"resend refused the message ({response.status_code}): {response.text}"
            )
