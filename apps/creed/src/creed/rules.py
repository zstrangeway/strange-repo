"""Stratagems, abilities and enhancements.

Stratagems are the biggest table in the export and the one most often wanted
under time pressure, which decides how they are filtered: in play the question
is not "what is this stratagem called" but "what can I do, in this phase, on
my turn, with the CP I have". So those are the filters, rather than a name
search that needs somebody to already know the answer.
"""

from dataclasses import dataclass

from .markup import to_markdown

# What the export writes in the `turn` column, and the two words people use.
YOUR_TURN = "Your turn"
OPPONENTS_TURN = "Opponent's turn"


@dataclass
class Stratagem:
    id: str
    name: str
    type: str
    cp: int | None
    turn: str
    phase: str
    detachment: str
    detachment_id: str
    faction_id: str
    description: str

    @property
    def either_turn(self) -> bool:
        return not (self.turn or "").strip()


def _stratagem(row) -> Stratagem:
    cost = (row["cp_cost"] or "").strip()
    return Stratagem(
        id=row["id"],
        name=row["name"],
        type=to_markdown(row["type"]),
        cp=int(cost) if cost.isdigit() else None,
        turn=(row["turn"] or "").strip(),
        phase=(row["phase"] or "").strip(),
        detachment=(row["detachment"] or "").strip(),
        detachment_id=(row["detachment_id"] or "").strip(),
        faction_id=(row["faction_id"] or "").strip(),
        description=to_markdown(row["description"]),
    )


def phases(connection) -> list[str]:
    """The phases the export actually names, for answering a bad one."""
    return [
        row["phase"]
        for row in connection.execute(
            'SELECT DISTINCT phase FROM "Stratagems" '
            "WHERE TRIM(phase) != '' ORDER BY phase"
        )
    ]


def stratagems(
    connection,
    name: str | None = None,
    phase: str | None = None,
    turn: str | None = None,
    detachment: str | None = None,
    faction: str | None = None,
    max_cp: int | None = None,
) -> list[Stratagem]:
    """Find stratagems by any combination of the things that matter in play.

    A stratagem with an empty `turn` or `phase` is usable in either or in any,
    so those rows match every filter rather than none — excluding them would
    quietly hide the core stratagems, which are the ones always available.
    """
    sql = 'SELECT * FROM "Stratagems" WHERE 1 = 1'
    parameters: list[object] = []
    if name:
        sql += " AND name LIKE ? COLLATE NOCASE"
        parameters.append(f"%{name.strip()}%")
    if phase:
        sql += " AND (TRIM(phase) = '' OR phase LIKE ? COLLATE NOCASE)"
        parameters.append(f"%{phase.strip()}%")
    if turn:
        sql += " AND (TRIM(turn) = '' OR turn LIKE ? COLLATE NOCASE)"
        parameters.append(f"%{turn.strip()}%")
    if detachment:
        sql += (
            " AND (TRIM(detachment_id) = '' OR detachment_id = ? "
            "OR detachment LIKE ? COLLATE NOCASE)"
        )
        parameters += [detachment, f"%{detachment}%"]
    if faction:
        sql += " AND (TRIM(faction_id) = '' OR faction_id = ? COLLATE NOCASE)"
        parameters.append(faction)
    sql += " ORDER BY CAST(cp_cost AS INTEGER), name"
    rows = [_stratagem(row) for row in connection.execute(sql, parameters)]
    if max_cp is not None:
        rows = [row for row in rows if row.cp is None or row.cp <= max_cp]
    return rows


def stratagems_for_datasheet(connection, datasheet_id: str) -> list[Stratagem]:
    return [
        _stratagem(row)
        for row in connection.execute(
            'SELECT s.* FROM "Datasheets_stratagems" ds '
            'JOIN "Stratagems" s ON s.id = ds.stratagem_id '
            "WHERE ds.datasheet_id = ? ORDER BY CAST(s.cp_cost AS INTEGER), s.name",
            (datasheet_id,),
        )
    ]


def abilities(connection, name: str) -> list[dict]:
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "faction_id": row["faction_id"],
            "description": to_markdown(row["description"]),
        }
        for row in connection.execute(
            'SELECT * FROM "Abilities" WHERE name LIKE ? COLLATE NOCASE ORDER BY name',
            (f"%{name.strip()}%",),
        )
    ]


def enhancements(
    connection, detachment: str | None = None, faction: str | None = None
) -> list[dict]:
    sql = 'SELECT * FROM "Enhancements" WHERE 1 = 1'
    parameters: list[object] = []
    if detachment:
        sql += " AND (detachment_id = ? OR detachment LIKE ? COLLATE NOCASE)"
        parameters += [detachment, f"%{detachment}%"]
    if faction:
        sql += " AND faction_id = ? COLLATE NOCASE"
        parameters.append(faction)
    sql += " ORDER BY CAST(cost AS INTEGER), name"
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "cost": int(row["cost"]) if (row["cost"] or "").strip().isdigit() else None,
            "detachment": row["detachment"],
            "detachment_id": row["detachment_id"],
            "faction_id": row["faction_id"],
            # Eligibility is a sentence, not a field. creed shows it and says
            # it has not decided it — see validation.
            "eligibility": to_markdown(row["description"]),
            "support_leader": (row["support_leader"] or "").strip().lower() == "true",
        }
        for row in connection.execute(sql, parameters)
    ]
