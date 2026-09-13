"""Somebody's army list, and what it costs.

The list is the one thing here that belongs to the person rather than to
Wahapedia, which is why it lives in its own tables and why a sync carries it
across rather than replacing it.

Pricing is the part that cannot be done unit by unit. Eleventh edition charges
by how many of a datasheet the army already holds, so a unit's cost is a
property of its position in the list rather than of the unit. Adding a third
Nobz costs more than the first did; removing one makes the survivors cheaper.
Nothing here caches a price for that reason — the total is computed from the
list as it stands, every time.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from . import datasheets, detachments


class ListError(Exception):
    """Something creed will not do to a list, with a reason somebody can act on."""


@dataclass
class PricedUnit:
    id: int
    datasheet_id: str
    name: str
    models: int
    ordinal: int
    tier: str
    unit_cost: int | None
    wargear: list[dict] = field(default_factory=list)
    enhancement: dict | None = None
    attached_to: int | None = None
    missing_from_export: bool = False

    @property
    def wargear_cost(self) -> int:
        return sum(item["cost"] * item["quantity"] for item in self.wargear)

    @property
    def enhancement_cost(self) -> int:
        return (self.enhancement or {}).get("cost") or 0

    @property
    def total(self) -> int:
        return (self.unit_cost or 0) + self.wargear_cost + self.enhancement_cost


@dataclass
class PricedList:
    id: int
    name: str
    faction_id: str
    points_limit: int
    detachment: detachments.Detachment | None
    units: list[PricedUnit] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(unit.total for unit in self.units)

    @property
    def remaining(self) -> int:
        return self.points_limit - self.total

    @property
    def over_by(self) -> int:
        return max(0, -self.remaining)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def create(connection, name: str, faction_id: str, points_limit: int) -> int:
    existing = connection.execute(
        "SELECT id FROM lists WHERE name = ?", (name,)
    ).fetchone()
    if existing:
        raise ListError(f"a list called {name!r} already exists")
    faction = connection.execute(
        'SELECT id FROM "Factions" WHERE id = ? COLLATE NOCASE '
        "OR name = ? COLLATE NOCASE",
        (faction_id, faction_id),
    ).fetchone()
    if faction is None:
        raise ListError(f"no faction called {faction_id!r} in the export")
    cursor = connection.execute(
        "INSERT INTO lists (name, faction_id, points_limit, created_at) "
        "VALUES (?, ?, ?, ?)",
        (name, faction["id"], points_limit, _now()),
    )
    return cursor.lastrowid


def _row(connection, list_id: int):
    row = connection.execute("SELECT * FROM lists WHERE id = ?", (list_id,)).fetchone()
    if row is None:
        raise ListError(f"no list with id {list_id}")
    return row


def set_detachment(connection, list_id: int, detachment_id: str) -> None:
    row = _row(connection, list_id)
    detachment = detachments.get(connection, detachment_id)
    if detachment is None:
        found = detachments.by_name(connection, detachment_id)
        detachment = found[0] if len(found) == 1 else None
    if detachment is None:
        raise ListError(f"no detachment called {detachment_id!r}")
    if detachment.faction_id != row["faction_id"]:
        available = [
            d.name for d in detachments.for_faction(connection, row["faction_id"])
        ]
        raise ListError(
            f"{detachment.name} belongs to {detachment.faction_id}, not "
            f"{row['faction_id']}. That faction has: {', '.join(available)}"
        )
    connection.execute(
        "UPDATE lists SET detachment_id = ? WHERE id = ?", (detachment.id, list_id)
    )


def add_unit(
    connection, list_id: int, datasheet_id: str, models: int | None = None
) -> int:
    row = _row(connection, list_id)
    sheet = datasheets.get(connection, datasheet_id)
    if sheet is None:
        raise ListError(f"no datasheet with id {datasheet_id!r}")
    sizes = sheet.points.sizes
    if models is None:
        models = sizes[0] if sizes else 1
    elif sizes and models not in sizes:
        raise ListError(
            f"{sheet.name} does not come in {models} models. "
            f"It comes in: {', '.join(str(size) for size in sizes)}"
        )
    position = (
        connection.execute(
            "SELECT COALESCE(MAX(position), 0) AS p FROM list_units WHERE list_id = ?",
            (list_id,),
        ).fetchone()["p"]
        + 1
    )
    cursor = connection.execute(
        "INSERT INTO list_units (list_id, datasheet_id, models, position, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (list_id, sheet.id, models, position, _now()),
    )
    _ = row
    return cursor.lastrowid


def remove_unit(connection, list_unit_id: int) -> None:
    row = connection.execute(
        "SELECT id FROM list_units WHERE id = ?", (list_unit_id,)
    ).fetchone()
    if row is None:
        raise ListError(f"no unit with id {list_unit_id} in any list")
    connection.execute("DELETE FROM list_units WHERE id = ?", (list_unit_id,))


def add_wargear(
    connection, list_unit_id: int, description: str, quantity: int = 1
) -> None:
    unit = connection.execute(
        "SELECT * FROM list_units WHERE id = ?", (list_unit_id,)
    ).fetchone()
    if unit is None:
        raise ListError(f"no unit with id {list_unit_id} in any list")
    sheet = datasheets.get(connection, unit["datasheet_id"])
    if sheet is None or sheet.points.wargear_cost(description) is None:
        available = (
            [option.description for option in sheet.points.wargear] if sheet else []
        )
        raise ListError(
            f"{description!r} is not a priced option on this datasheet. "
            f"It has: {', '.join(available) if available else 'none'}"
        )
    connection.execute(
        "INSERT INTO list_unit_wargear (list_unit_id, description, quantity) "
        "VALUES (?, ?, ?)",
        (list_unit_id, description, quantity),
    )


def set_enhancement(connection, list_unit_id: int, enhancement_id: str | None) -> None:
    unit = connection.execute(
        "SELECT * FROM list_units WHERE id = ?", (list_unit_id,)
    ).fetchone()
    if unit is None:
        raise ListError(f"no unit with id {list_unit_id} in any list")
    connection.execute(
        "UPDATE list_units SET enhancement_id = ? WHERE id = ?",
        (enhancement_id, list_unit_id),
    )


def attach(connection, leader_unit_id: int, target_unit_id: int | None) -> None:
    connection.execute(
        "UPDATE list_units SET attached_to = ? WHERE id = ?",
        (target_unit_id, leader_unit_id),
    )


def price(connection, list_id: int) -> PricedList:
    """Compute the list as it stands, ordinals and all."""
    row = _row(connection, list_id)
    detachment = (
        detachments.get(connection, row["detachment_id"])
        if row["detachment_id"]
        else None
    )
    priced = PricedList(
        id=row["id"],
        name=row["name"],
        faction_id=row["faction_id"],
        points_limit=row["points_limit"],
        detachment=detachment,
    )
    seen: dict[str, int] = {}
    for unit in connection.execute(
        "SELECT * FROM list_units WHERE list_id = ? ORDER BY position, id", (list_id,)
    ):
        # The ordinal is what the price depends on: this is the nth unit of
        # this datasheet in the list, counting in the order they were added.
        ordinal = seen.get(unit["datasheet_id"], 0) + 1
        seen[unit["datasheet_id"]] = ordinal
        sheet = datasheets.get(connection, unit["datasheet_id"])
        if sheet is None:
            priced.units.append(
                PricedUnit(
                    id=unit["id"],
                    datasheet_id=unit["datasheet_id"],
                    name=unit["datasheet_id"],
                    models=unit["models"],
                    ordinal=ordinal,
                    tier="",
                    unit_cost=None,
                    missing_from_export=True,
                )
            )
            continue
        tier = sheet.points.tier_for(ordinal)
        entry = PricedUnit(
            id=unit["id"],
            datasheet_id=sheet.id,
            name=sheet.name,
            models=unit["models"],
            ordinal=ordinal,
            tier=tier.label if tier else "",
            unit_cost=sheet.points.cost_for(unit["models"], ordinal),
            attached_to=unit["attached_to"],
        )
        for gear in connection.execute(
            "SELECT description, quantity FROM list_unit_wargear "
            "WHERE list_unit_id = ?",
            (unit["id"],),
        ):
            cost = sheet.points.wargear_cost(gear["description"])
            entry.wargear.append(
                {
                    "description": gear["description"],
                    "quantity": gear["quantity"],
                    "cost": cost or 0,
                }
            )
        if unit["enhancement_id"]:
            enhancement = connection.execute(
                'SELECT * FROM "Enhancements" WHERE id = ?', (unit["enhancement_id"],)
            ).fetchone()
            if enhancement is not None:
                cost = (enhancement["cost"] or "").strip()
                entry.enhancement = {
                    "id": enhancement["id"],
                    "name": enhancement["name"],
                    "cost": int(cost) if cost.isdigit() else 0,
                    "detachment_id": enhancement["detachment_id"],
                    "eligibility": enhancement["description"],
                }
        priced.units.append(entry)
    return priced


def all_lists(connection) -> list[dict]:
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "faction_id": row["faction_id"],
            "points_limit": row["points_limit"],
        }
        for row in connection.execute("SELECT * FROM lists ORDER BY name")
    ]
