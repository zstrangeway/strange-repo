"""The Anthropic provider.

The key is the user's, read from their environment, used from their machine.
scout never proxies a call through anything of ours and never writes the key
anywhere — which is the whole of what "bring your own model" has to mean to be
worth saying.
"""

import os

import anthropic

from ..errors import ScoutError
from .prompt import SYSTEM, request

DEFAULT_MODEL = "claude-sonnet-5"

API_KEY_VARIABLE = "ANTHROPIC_API_KEY"


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("SCOUT_MODEL", DEFAULT_MODEL)

    def tailor(self, *, master: str, posting: str) -> str:
        if not os.environ.get(API_KEY_VARIABLE):
            raise ScoutError(
                f"{API_KEY_VARIABLE} is not set.",
                detail=(
                    "scout uses your own Anthropic key and never stores it. "
                    f"Set it with: export {API_KEY_VARIABLE}=sk-ant-..."
                ),
            )

        client = anthropic.Anthropic()
        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM,
                # Medium rather than the default: this is a rewrite of a
                # document that is already written, not a reasoning problem,
                # and effort is the first thing that shows up on the bill.
                output_config={"effort": "medium"},
                messages=[{"role": "user", "content": request(master, posting)}],
            )
        except anthropic.APIStatusError as exc:
            raise ScoutError(
                f"The model call failed: {exc.status_code} from Anthropic.",
                detail=str(getattr(exc, "message", exc)),
            ) from exc
        except anthropic.APIError as exc:
            raise ScoutError(f"The model call failed: {exc}") from exc

        if response.stop_reason == "refusal":
            raise ScoutError("The model call failed: the model declined this request.")

        draft = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        if not draft:
            raise ScoutError("The model call failed: it returned nothing.")
        return draft
