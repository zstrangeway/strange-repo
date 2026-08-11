"""Who narrates, and whether it is the real thing.

Selected from the environment once, the same arrangement as ``identity``:

    GM_FAKE          set to 1 to use the spec double
    OPENROUTER_API_KEY   the key the real narrator needs
    GM_MODEL         which model to ask for, default anthropic/claude-opus-5

The real narrator goes through OpenRouter, which serves an OpenAI-compatible
API and no Anthropic one — so the client is the openai SDK pointed at a
different base url, not the anthropic SDK.
"""

import os
from functools import cache

from gary_api import logs
from gary_api.narration.base import (
    Call,
    Calls,
    NarrationError,
    Narrator,
    Prompt,
    Refused,
    Result,
    Said,
    TOOLS,
)
from gary_api.narration.fake import FakeNarrator

__all__ = [
    "Call",
    "Calls",
    "NarrationError",
    "Narrator",
    "Prompt",
    "Refused",
    "Result",
    "Said",
    "TOOLS",
    "faking",
    "narrator",
    "report_configuration",
]

logger = logs.get_logger(__name__)

DEFAULT_MODEL = "anthropic/claude-opus-5"


def faking() -> bool:
    """Whether the spec double is standing in for the model."""
    return os.environ.get("GM_FAKE") == "1"


def model() -> str:
    return os.environ.get("GM_MODEL", DEFAULT_MODEL)


@cache
def narrator() -> Narrator:
    """The narrator this deployment uses. Built once, then reused."""
    if faking():
        return FakeNarrator()

    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise NarrationError("missing OPENROUTER_API_KEY")

    # Imported here rather than at module scope so a deployment running the
    # double does not need the SDK installed to start.
    from gary_api.narration.openrouter import OpenRouterNarrator

    return OpenRouterNarrator(api_key=key, model=model())


def report_configuration() -> None:
    """Say at startup whether anybody can play.

    A missing key is not a reason to refuse to start — the rest of gary works
    and somebody has to be able to sign in to fix it — but it must not be
    discovered by a player halfway through a sentence either.
    """
    if faking():
        logger.warning("narration.faking")
        return

    try:
        narrator()
    except NarrationError as error:
        logger.error("narration.misconfigured", reason=str(error))
    else:
        logger.info("narration.configured", model=model())
