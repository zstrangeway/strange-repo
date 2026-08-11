"""The systems gary runs.

One file per system, each carrying its own data and its own resolution, and
one line in ``REGISTRY`` to turn it on. That is the whole of adding a system:
nothing in ``narration``, ``world`` or ``play`` learns a new name, because
none of them knows any of the existing ones either.

The registry is a tuple and not a scan of the directory. A file that is
present but not listed is a system somebody is still writing, and finding out
by seeing it offered to players is the wrong way round.
"""

from gary_api.systems.add_1e import ADnD1e
from gary_api.systems.base import (
    Degree,
    Module,
    Outcome,
    Ruleset,
    SystemError,
)
from gary_api.systems.dnd_3_5e import DnD35e
from gary_api.systems.dnd_5e import DnD5e
from gary_api.systems.pathfinder_2e import Pathfinder2e

__all__ = [
    "Degree",
    "Module",
    "Outcome",
    "Ruleset",
    "SystemError",
    "character_class",
    "module",
    "ruleset",
    "rulesets",
]

REGISTRY: tuple[Ruleset, ...] = (
    DnD5e(),
    DnD35e(),
    ADnD1e(),
    Pathfinder2e(),
)


def rulesets() -> tuple[Ruleset, ...]:
    """Everything gary runs, in the order to offer it."""
    return REGISTRY


def ruleset(slug: str) -> Ruleset:
    """The named system. Raises SystemError when gary does not run it."""
    for candidate in REGISTRY:
        if candidate.slug == slug:
            return candidate

    raise SystemError(f"gary does not run {slug!r}")


def module(system_slug: str, module_slug: str) -> Module:
    """The named module of the named system.

    The pair has to agree. A module that exists, under a system that exists,
    but not under that one, is the mistake two dropdowns make easy — so it is
    refused rather than resolved to whichever system happens to have it.
    """
    found = ruleset(system_slug)
    for candidate in found.modules:
        if candidate.slug == module_slug:
            return candidate

    raise SystemError(f"{found.name} has no module {module_slug!r}")


def character_class(system_slug: str, name: str) -> str:
    """The named class, as the system spells it.

    Refusing here is what stops an artificer turning up in a game that has
    none, which is otherwise something the model discovers mid-scene and has
    to improvise around.
    """
    found = ruleset(system_slug)
    wanted = (name or "").strip().lower()
    for candidate in found.classes:
        if candidate == wanted:
            return candidate

    raise SystemError(f"{found.name} has no {name!r}")
