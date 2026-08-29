"""The OpenRouter provider — the only one scout has.

A router rather than one vendor, which is why it is the only one needed: the
default model is a Claude, and `SCOUT_MODEL` reaches everything else it serves
without scout learning a second API. Its `:free` models are also what let
`scout-smoke` exercise this exact path for no money.

It uses the `openai` client even though the model on the other end is usually
a Claude, for the reason gary-api records in its own dependencies:
**OpenRouter serves an OpenAI-compatible API and no Anthropic one.** Pointing
the Anthropic SDK at it does not work, which is why there is no code here that
tries.
"""

import os

import openai

from ..errors import ScoutError
from .prompt import STRUCTURE, SYSTEM, request

BASE_URL = "https://openrouter.ai/api/v1"

API_KEY_VARIABLE = "OPENROUTER_API_KEY"

# Sonnet 5, because that is the paid default this repo works to, reached
# through the router rather than through Anthropic directly. `SCOUT_MODEL`
# takes any id OpenRouter serves, in its `<vendor>/<model>` form.
DEFAULT_MODEL = "anthropic/claude-sonnet-5"


class OpenRouterProvider:
    name = "openrouter"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("SCOUT_MODEL", DEFAULT_MODEL)

    def structure(self, *, resume: str) -> str:
        return self._ask(STRUCTURE, resume)

    def tailor(self, *, master: str, posting: str) -> str:
        return self._ask(SYSTEM, request(master, posting))

    def _ask(self, system: str, user: str) -> str:
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
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
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
