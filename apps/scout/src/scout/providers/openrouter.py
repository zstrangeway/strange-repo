"""The OpenRouter provider.

Here because it is the key most likely to already be on the machine, and
because OpenRouter is the only way to run scout's smoke check for nothing: its
`:free` models cost no money and exercise this exact path.

It uses the `openai` client rather than the `anthropic` one even when the
model on the other end is a Claude, for the reason gary-api records in its own
dependencies: **OpenRouter serves an OpenAI-compatible API and no Anthropic
one.** Pointing the Anthropic SDK at it does not work.
"""

import os

import openai

from ..errors import ScoutError
from .prompt import SYSTEM, request

BASE_URL = "https://openrouter.ai/api/v1"

API_KEY_VARIABLE = "OPENROUTER_API_KEY"

# Sonnet 5 in OpenRouter's namespace, because that is the paid default this
# repo works to. `SCOUT_MODEL` takes a model id in whichever provider's
# namespace is selected — `<vendor>/<model>` here, a bare id for Anthropic.
DEFAULT_MODEL = "anthropic/claude-sonnet-5"


class OpenRouterProvider:
    name = "openrouter"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("SCOUT_MODEL", DEFAULT_MODEL)

    def tailor(self, *, master: str, posting: str) -> str:
        key = os.environ.get(API_KEY_VARIABLE)
        if not key:
            raise ScoutError(
                f"{API_KEY_VARIABLE} is not set.",
                detail=(
                    "scout uses your own OpenRouter key and never stores it. "
                    f"Set it with: export {API_KEY_VARIABLE}=sk-or-..."
                ),
            )

        client = openai.OpenAI(base_url=BASE_URL, api_key=key)
        try:
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=16000,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": request(master, posting)},
                ],
            )
        except openai.APIStatusError as exc:
            raise ScoutError(
                f"The model call failed: {exc.status_code} from OpenRouter.",
                detail=str(getattr(exc, "message", exc)),
            ) from exc
        except openai.APIError as exc:
            raise ScoutError(f"The model call failed: {exc}") from exc

        # OpenRouter routes to whoever is cheapest and up, so a model can
        # answer with no choices at all — a provider outage downstream arrives
        # here as an empty list rather than as an error.
        if not response.choices:
            raise ScoutError(
                "The model call failed: OpenRouter returned no choices.",
                detail="Usually a downstream provider being down for that model.",
            )

        draft = (response.choices[0].message.content or "").strip()
        if not draft:
            raise ScoutError("The model call failed: it returned nothing.")
        return draft
