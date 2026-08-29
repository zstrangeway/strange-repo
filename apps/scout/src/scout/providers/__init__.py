"""Where a model gets asked for a draft.

One interface, two implementations. Anthropic is the default; OpenRouter is
there because it is the key most likely to be on the machine already, and
because its `:free` models are the only way to run `scout-smoke` for nothing.

Both send the same instruction, from `prompt.py`. Two providers with two
slightly different versions of it is the failure nobody notices.

A provider returns markdown and nothing else. It is deliberately not asked to
report what it changed: `summary.py` works that out by diffing the documents,
and a model asked what it changed reports what it meant to change.
"""

from typing import Protocol

from ..errors import ScoutError


class Provider(Protocol):
    """Turns a master resume and a posting into a tailored draft."""

    name: str

    def tailor(self, *, master: str, posting: str) -> str:
        """Return the draft as markdown, or raise ``ScoutError``."""
        ...


def load(name: str = "anthropic") -> Provider:
    """The provider by name.

    Imported here rather than at module scope so that `scout save` and
    `scout log` — which need no model at all — do not pay for importing an
    SDK, or fail because one is misconfigured.
    """
    if name == "anthropic":
        from .anthropic_api import AnthropicProvider

        return AnthropicProvider()
    if name == "openrouter":
        from .openrouter import OpenRouterProvider

        return OpenRouterProvider()
    if name == "fake":
        from .fake import FakeProvider

        return FakeProvider()
    raise ScoutError(
        f'There is no provider called "{name}".',
        detail="scout ships with: anthropic, openrouter.",
    )
