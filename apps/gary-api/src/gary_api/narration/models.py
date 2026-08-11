"""Which models gary can be run on — not to be confused with gary_api.models,
which is the database.

OpenRouter serves hundreds at prices two orders of magnitude apart, so the
choice is worth exposing. This is the list a person picks from, and the one
rule it enforces.

**Only models that can call tools.** gary's whole design is the model going
through the engines: it asks for a check, the rules grade it, the world
records it. A model without function calling cannot do any of that, and it
would not fail loudly — it would narrate a perfectly plausible game that
nothing was adjudicating. So the filter is not a nicety, and choosing outside
the list is refused rather than warned about.

The live list is fetched from OpenRouter and cached for the process. Without
a key — or with OpenRouter unreachable — gary offers ``BUILT_IN`` instead, so
the app still starts and still plays. The specs run that way, which is what
makes them deterministic.
"""

import os
from dataclasses import dataclass

import httpx

from gary_api import logs

logger = logs.get_logger(__name__)

CATALOGUE_URL = "https://openrouter.ai/api/v1/models"

# How long to wait on somebody else's API before falling back. This sits in
# front of a menu, so a slow answer is worse than a shorter list.
TIMEOUT = 8.0


class ModelError(Exception):
    """A model gary cannot, or will not, run on."""


@dataclass(frozen=True)
class Model:
    id: str
    name: str
    # Dollars per million tokens, which is the unit the difference is legible
    # in. Fractions of a cent per token are not something anyone can compare.
    prompt_cost: float
    completion_cost: float
    context: int
    reasons: bool
    # Somewhere to start, for a list that is otherwise hundreds long. These
    # are picked on price and reputation and not on evidence that they hold
    # gary's tool discipline — the smoke task is what would make them that.
    suggested: bool = False


BUILT_IN: tuple[Model, ...] = (
    Model(
        "anthropic/claude-opus-5", "Claude Opus 5", 5.0, 25.0, 1_000_000, True, True
    ),
    Model(
        "anthropic/claude-sonnet-5", "Claude Sonnet 5", 2.0, 10.0, 1_000_000, True, True
    ),
    Model(
        "anthropic/claude-haiku-4.5", "Claude Haiku 4.5", 1.0, 5.0, 200_000, False
    ),
    Model(
        "deepseek/deepseek-v3.2", "DeepSeek V3.2", 0.27, 0.40, 163_840, True, True
    ),
    Model("z-ai/glm-4.7", "GLM 4.7", 0.40, 1.75, 204_800, True),
    Model("moonshotai/kimi-k2.5", "Kimi K2.5", 0.57, 2.85, 262_144, True),
    Model("qwen/qwen3.7-plus", "Qwen3.7 Plus", 0.32, 1.28, 1_000_000, True),
)

# Which of the fetched list to put at the top. Kept small on purpose: a
# suggestion that covers everything suggests nothing.
SUGGESTED = tuple(model.id for model in BUILT_IN if model.suggested)

_cached: tuple[Model, ...] | None = None


def _key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "")


def _as_model(row: dict) -> Model | None:
    pricing = row.get("pricing") or {}
    try:
        prompt = float(pricing.get("prompt") or 0)
        completion = float(pricing.get("completion") or 0)
    except (TypeError, ValueError):
        return None

    identifier = row.get("id") or ""
    if not identifier:
        return None

    return Model(
        id=identifier,
        name=row.get("name") or identifier,
        prompt_cost=round(prompt * 1_000_000, 4),
        completion_cost=round(completion * 1_000_000, 4),
        context=int(row.get("context_length") or 0),
        reasons="reasoning" in (row.get("supported_parameters") or []),
        suggested=identifier in SUGGESTED,
    )


def fetch() -> tuple[Model, ...]:
    """Ask OpenRouter what it serves, keeping only what gary can use."""
    response = httpx.get(
        CATALOGUE_URL,
        timeout=TIMEOUT,
        headers={"authorization": f"Bearer {_key()}"} if _key() else {},
    )
    response.raise_for_status()

    found = []
    for row in response.json().get("data") or []:
        if "tools" not in (row.get("supported_parameters") or []):
            # Cannot call a tool, so cannot play gary. Left out rather than
            # shown greyed out: a model in the list is one that works.
            continue
        model = _as_model(row)
        if model is not None:
            found.append(model)

    return tuple(found)


def available() -> tuple[Model, ...]:
    """Everything gary can be run on, suggestions first.

    Cached for the life of the process. OpenRouter's catalogue changes over
    days, not minutes, and a menu that re-fetches per request would put
    somebody else's latency in front of every page load.
    """
    global _cached
    if _cached is not None:
        return _cached

    if not _key():
        logger.warning("models.built_in", reason="no OPENROUTER_API_KEY")
        _cached = BUILT_IN
        return _cached

    try:
        found = fetch()
    except Exception as error:
        # A menu is not worth failing a request over, but a short list that
        # looks complete is exactly the kind of quiet wrongness worth logging.
        logger.error("models.unreachable", reason=str(error))
        _cached = BUILT_IN
        return _cached

    if not found:
        logger.error("models.empty", reason="nothing served that can call tools")
        _cached = BUILT_IN
        return _cached

    _cached = tuple(
        sorted(found, key=lambda model: (not model.suggested, model.completion_cost))
    )
    logger.info("models.fetched", count=len(_cached))
    return _cached


def forget() -> None:
    """Drop the cache. For the specs, and for a process that wants a re-read."""
    global _cached
    _cached = None


def model(identifier: str) -> Model:
    """The named model, if gary offers it."""
    for candidate in available():
        if candidate.id == identifier:
            return candidate

    raise ModelError(f"gary cannot run on {identifier!r}")


def default() -> str:
    """What a campaign that names no model runs on."""
    return os.environ.get("GM_MODEL", BUILT_IN[0].id)
