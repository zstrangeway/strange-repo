"""Reading a datasheet, which lives in eight tables.

A datasheet in the export is the sheet itself plus its models' statlines, its
wargear, its abilities, its keywords, its unit composition, its points, and
who it can lead. Handing back one of those is not an answer to "what is a
Custodian Guard"; putting them together is the whole job.
"""

from dataclasses import dataclass, field

from . import pricing
from .markup import to_markdown

# Battlefield Role has no column in the 11th edition export: `role` is present
# in the specification and empty on all 1,660 datasheets, because the role now
# lives among the keywords. Deriving it from there is the difference between
# every search result carrying a blank field and it carrying the thing people
# actually filter by.
ROLE_KEYWORDS = (
    "Epic Hero",
    "Character",
    "Battleline",
    "Dedicated Transport",
    "Fortification",
    "Transport",
    "Vehicle",
    "Monster",
    "Infantry",
)


def role_from_keywords(keywords) -> str:
    """The first role keyword the datasheet carries, most specific first."""
    held = {keyword.strip().casefold() for keyword in keywords if keyword}
    for role in ROLE_KEYWORDS:
        if role.casefold() in held:
            return role
    return ""


# A search that matches a great many has answered nothing if it returns them
# all: fifty full datasheets fill a model's context and say less than five do.
SEARCH_LIMIT = 25


@dataclass
class Match:
    """A search hit: enough to choose between, not the whole datasheet."""

    id: str
    name: str
    faction: str
    role: str
    link: str


@dataclass
class SearchResult:
    matches: list[Match]
    total: int
    query: str

    @property
    def truncated(self) -> bool:
        return self.total > len(self.matches)


@dataclass
class Datasheet:
    id: str
    name: str
    faction: str
    faction_id: str
    role: str
    legend: str
    loadout: str
    transport: str
    link: str
    virtual: bool
    is_support: bool
    models: list[dict] = field(default_factory=list)
    wargear: list[dict] = field(default_factory=list)
    abilities: list[dict] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    faction_keywords: list[str] = field(default_factory=list)
    composition: list[str] = field(default_factory=list)
    options: list[str] = field(default_factory=list)
    leads: list[dict] = field(default_factory=list)
    led_by: list[dict] = field(default_factory=list)
    damaged: dict | None = None
    points: pricing.Pricing = field(default_factory=pricing.Pricing)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() == "true"


def search(connection, query: str, faction: str | None = None) -> SearchResult:
    """Find datasheets by part of a name, optionally within one faction.

    Deliberately not a single-result lookup even for an exact name: several
    factions have a datasheet called Captain, and picking one silently is how
    somebody ends up quoting the wrong statline.
    """
    text = (query or "").strip()
    if not text:
        return SearchResult(matches=[], total=0, query=text)
    sql = (
        "SELECT d.id, d.name, d.link, f.name AS faction, "
        "(SELECT GROUP_CONCAT(k.keyword, '|') FROM \"Datasheets_keywords\" k "
        " WHERE k.datasheet_id = d.id) AS keywords "
        'FROM "Datasheets" d LEFT JOIN "Factions" f ON f.id = d.faction_id '
        "WHERE d.name LIKE ? COLLATE NOCASE"
    )
    parameters: list[object] = [f"%{text}%"]
    if faction:
        sql += " AND (d.faction_id = ? COLLATE NOCASE OR f.name = ? COLLATE NOCASE)"
        parameters += [faction, faction]
    sql += " ORDER BY LENGTH(d.name), d.name"
    rows = connection.execute(sql, parameters).fetchall()
    matches = [
        Match(
            id=row["id"],
            name=row["name"],
            faction=row["faction"] or row["id"],
            role=role_from_keywords((row["keywords"] or "").split("|")),
            link=row["link"] or "",
        )
        for row in rows[:SEARCH_LIMIT]
    ]
    return SearchResult(matches=matches, total=len(rows), query=text)


def get(connection, datasheet_id: str) -> Datasheet | None:
    """Assemble one datasheet from every table that has a piece of it."""
    row = connection.execute(
        'SELECT d.*, f.name AS faction_name FROM "Datasheets" d '
        'LEFT JOIN "Factions" f ON f.id = d.faction_id WHERE d.id = ?',
        (datasheet_id,),
    ).fetchone()
    if row is None:
        return None

    sheet = Datasheet(
        id=row["id"],
        name=row["name"],
        faction=row["faction_name"] or row["faction_id"],
        faction_id=row["faction_id"],
        role="",
        legend=to_markdown(row["legend"]),
        loadout=to_markdown(row["loadout"]),
        transport=to_markdown(row["transport"]),
        link=row["link"] or "",
        virtual=_truthy(row["virtual"]),
        is_support=_truthy(row["is_support"]),
    )

    # Multi-model units have a statline per profile and the export keeps them
    # as separate rows. Reading only the first loses the sergeant.
    sheet.models = [
        {
            "name": model["name"],
            "M": model["M"],
            "T": model["T"],
            "Sv": model["Sv"],
            "invulnerable": model["inv_sv"],
            "invulnerable_note": to_markdown(model["inv_sv_descr"]),
            "W": model["W"],
            "Ld": model["Ld"],
            "OC": model["OC"],
            "base": model["base_size"],
        }
        for model in connection.execute(
            'SELECT * FROM "Datasheets_models" WHERE datasheet_id = ? '
            "ORDER BY CAST(line AS INTEGER)",
            (datasheet_id,),
        )
    ]

    sheet.wargear = [
        {
            "name": gear["name"],
            "profile": gear["description"] and to_markdown(gear["description"]),
            "range": gear["range"],
            "type": to_markdown(gear["type"]),
            "A": gear["A"],
            "BS_WS": gear["BS_WS"],
            "S": gear["S"],
            "AP": gear["AP"],
            "D": gear["D"],
        }
        for gear in connection.execute(
            'SELECT * FROM "Datasheets_wargear" WHERE datasheet_id = ? '
            "ORDER BY CAST(line AS INTEGER), CAST(line_in_wargear AS INTEGER)",
            (datasheet_id,),
        )
    ]

    # An ability row either carries its own text or points at Abilities.csv,
    # and the shared ones are the ones people ask about by name.
    sheet.abilities = [
        {
            "name": ability["name"] or ability["shared_name"],
            "type": ability["type"],
            "parameter": ability["parameter"],
            "model": ability["model"],
            "description": to_markdown(
                ability["description"] or ability["shared_description"]
            ),
        }
        for ability in connection.execute(
            "SELECT da.*, a.name AS shared_name, a.description AS shared_description "
            'FROM "Datasheets_abilities" da '
            'LEFT JOIN "Abilities" a ON a.id = da.ability_id '
            "WHERE da.datasheet_id = ? ORDER BY CAST(da.line AS INTEGER)",
            (datasheet_id,),
        )
    ]

    for keyword in connection.execute(
        'SELECT keyword, is_faction_keyword FROM "Datasheets_keywords" '
        "WHERE datasheet_id = ?",
        (datasheet_id,),
    ):
        target = (
            sheet.faction_keywords
            if _truthy(keyword["is_faction_keyword"])
            else sheet.keywords
        )
        if keyword["keyword"] and keyword["keyword"] not in target:
            target.append(keyword["keyword"])

    sheet.role = role_from_keywords(sheet.keywords + sheet.faction_keywords)

    sheet.composition = [
        to_markdown(entry["description"])
        for entry in connection.execute(
            'SELECT description FROM "Datasheets_unit_composition" '
            "WHERE datasheet_id = ? ORDER BY CAST(line AS INTEGER)",
            (datasheet_id,),
        )
    ]

    sheet.options = [
        to_markdown(entry["description"])
        for entry in connection.execute(
            'SELECT description FROM "Datasheets_options" WHERE datasheet_id = ? '
            "ORDER BY CAST(line AS INTEGER)",
            (datasheet_id,),
        )
    ]

    sheet.leads = [
        {"id": led["id"], "name": led["name"]}
        for led in connection.execute(
            'SELECT d.id, d.name FROM "Datasheets_leader" l '
            'JOIN "Datasheets" d ON d.id = l.attached_id '
            "WHERE l.leader_id = ? ORDER BY d.name",
            (datasheet_id,),
        )
    ]
    sheet.led_by = [
        {"id": leader["id"], "name": leader["name"]}
        for leader in connection.execute(
            'SELECT d.id, d.name FROM "Datasheets_leader" l '
            'JOIN "Datasheets" d ON d.id = l.leader_id '
            "WHERE l.attached_id = ? ORDER BY d.name",
            (datasheet_id,),
        )
    ]

    if (row["damaged_w"] or "").strip():
        sheet.damaged = {
            "wounds": row["damaged_w"],
            "effect": to_markdown(row["damaged_description"]),
        }

    sheet.points = pricing.parse(
        connection.execute(
            'SELECT line, description, cost FROM "Datasheets_models_cost" '
            "WHERE datasheet_id = ?",
            (datasheet_id,),
        ).fetchall()
    )
    return sheet


def by_name(connection, name: str, faction: str | None = None) -> list[Datasheet]:
    """Every datasheet with exactly this name — often more than one."""
    sql = (
        'SELECT d.id FROM "Datasheets" d LEFT JOIN "Factions" f '
        "ON f.id = d.faction_id WHERE d.name = ? COLLATE NOCASE"
    )
    parameters: list[object] = [name.strip()]
    if faction:
        sql += " AND (d.faction_id = ? COLLATE NOCASE OR f.name = ? COLLATE NOCASE)"
        parameters += [faction, faction]
    return [
        sheet
        for sheet in (
            get(connection, row["id"]) for row in connection.execute(sql, parameters)
        )
        if sheet is not None
    ]


def factions(connection) -> list[dict]:
    return [
        {"id": row["id"], "name": row["name"], "link": row["link"]}
        for row in connection.execute(
            'SELECT id, name, link FROM "Factions" ORDER BY name'
        )
    ]


def in_faction(connection, faction: str) -> list[Match]:
    rows = connection.execute(
        "SELECT d.id, d.name, d.link, f.name AS faction, "
        "(SELECT GROUP_CONCAT(k.keyword, '|') FROM \"Datasheets_keywords\" k "
        " WHERE k.datasheet_id = d.id) AS keywords "
        'FROM "Datasheets" d LEFT JOIN "Factions" f ON f.id = d.faction_id '
        "WHERE d.faction_id = ? COLLATE NOCASE OR f.name = ? COLLATE NOCASE "
        "ORDER BY d.name",
        (faction, faction),
    ).fetchall()
    return [
        Match(
            id=row["id"],
            name=row["name"],
            faction=row["faction"] or faction,
            role=role_from_keywords((row["keywords"] or "").split("|")),
            link=row["link"] or "",
        )
        for row in rows
    ]
