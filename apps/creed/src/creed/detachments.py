"""Detachments: the hinge of an 11th edition army.

A detachment decides the army rule, the stratagems, the enhancements, and —
new this edition — how many Detachment Points the army gets and what its Force
Disposition is.

Detachment Points are not a property of the detachment alone.
``Detachments_chapter_dp`` overrides them for named keywords, so the same
Space Marines detachment gives a different number to Black Templars than to
Blood Angels. Reading only ``Detachments`` gives the wrong number for exactly
the armies most likely to be asked about.
"""

from dataclasses import dataclass, field

from . import rules
from .markup import to_markdown


@dataclass
class Detachment:
    id: str
    name: str
    faction_id: str
    faction: str
    type: str
    dp: int | None
    force_disposition: str
    chapter_dp: dict[str, int] = field(default_factory=dict)
    ability: dict | None = None

    @property
    def dp_varies(self) -> bool:
        return bool(self.chapter_dp)

    def dp_for(self, keyword: str | None = None) -> int | None:
        """The points for one chapter, falling back to the detachment's own."""
        if keyword:
            for name, value in self.chapter_dp.items():
                if name.casefold() == keyword.casefold():
                    return value
        return self.dp


def _number(value) -> int | None:
    text = (value or "").strip()
    return int(text) if text.lstrip("-").isdigit() else None


def _build(connection, row) -> Detachment:
    detachment = Detachment(
        id=row["id"],
        name=row["name"],
        faction_id=row["faction_id"],
        faction=row["faction_name"] or row["faction_id"],
        type=(row["type"] or "").strip(),
        dp=_number(row["dp"]),
        force_disposition=(row["force_disposition"] or "").strip(),
    )
    for override in connection.execute(
        'SELECT keyword, dp FROM "Detachments_chapter_dp" WHERE detachment_id = ?',
        (row["id"],),
    ):
        value = _number(override["dp"])
        if value is not None:
            detachment.chapter_dp[override["keyword"]] = value
    ability = connection.execute(
        'SELECT * FROM "Detachment_abilities" WHERE detachment_id = ? LIMIT 1',
        (row["id"],),
    ).fetchone()
    if ability is not None:
        detachment.ability = {
            "name": ability["name"],
            "description": to_markdown(ability["description"]),
        }
    return detachment


_SELECT = (
    'SELECT d.*, f.name AS faction_name FROM "Detachments" d '
    'LEFT JOIN "Factions" f ON f.id = d.faction_id'
)


def for_faction(connection, faction: str) -> list[Detachment]:
    rows = connection.execute(
        f"{_SELECT} WHERE d.faction_id = ? COLLATE NOCASE "
        "OR f.name = ? COLLATE NOCASE ORDER BY d.name",
        (faction, faction),
    ).fetchall()
    return [_build(connection, row) for row in rows]


def by_name(connection, name: str) -> list[Detachment]:
    rows = connection.execute(
        f"{_SELECT} WHERE d.name LIKE ? COLLATE NOCASE ORDER BY d.name",
        (f"%{name.strip()}%",),
    ).fetchall()
    return [_build(connection, row) for row in rows]


def get(connection, detachment_id: str) -> Detachment | None:
    row = connection.execute(f"{_SELECT} WHERE d.id = ?", (detachment_id,)).fetchone()
    return _build(connection, row) if row else None


def contents(connection, detachment_id: str) -> dict:
    """Everything a detachment brings, which is the reason to pick one."""
    detachment = get(connection, detachment_id)
    if detachment is None:
        return {}
    return {
        "detachment": detachment,
        "stratagems": rules.stratagems(connection, detachment=detachment_id),
        "enhancements": rules.enhancements(connection, detachment=detachment_id),
    }
