"""What Wahapedia's data export contains, and where it lives.

The table list here is transcribed from the export's own specification
workbook (``Export Data Specs.xlsx``), not assembled by trying filenames that
looked plausible. That distinction cost something to learn: guessing produced
a list of nineteen that every server answered 200 for, and the two it missed —
``Detachments`` and ``Detachments_chapter_dp`` — are the entire basis of the
detachment feature. A missing table is not an error anywhere; it is a feature
that quietly returns nothing.

Eleventh edition, deliberately. The tenth edition export is still served and
still answers every request, but it has not moved since 2026-06-13. Pointing
at it would mean an app whose specs all pass and whose data is permanently
out of date, which is the one thing this app exists not to be.
"""

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://wahapedia.ru/wh40k11ed"


def base_url() -> str:
    """Where the export lives.

    Overridable so the specs can serve their own copy on localhost. A spec
    that reached the real site would fail whenever somebody was on a train,
    and would be testing Wahapedia's uptime rather than creed.
    """
    return os.environ.get("CREED_EXPORT_BASE", DEFAULT_BASE_URL).rstrip("/")


# Pipe-delimited, UTF-8 with a BOM. The BOM is not cosmetic: it lands on the
# first header name, so decoding as plain utf-8 leaves the first column called
# "\ufeffid" and every join against it misses without erroring.
DELIMITER = "|"
ENCODING = "utf-8-sig"

# Wahapedia asks for this in the export's own terms: "When publishing your
# work, mentioning Wahapedia is highly recommended. For example, with the
# inscription 'powered by Wahapedia'." The data is the whole product, so the
# credit travels with the answers rather than living only in the README.
ATTRIBUTION = "Data from Wahapedia (https://wahapedia.ru) — powered by Wahapedia"

# The file that says whether anything changed. Thirty-nine bytes, covering the
# whole export, which is what makes checking often affordable.
UPDATE_MARKER = "Last_update"


@dataclass(frozen=True)
class Table:
    """One CSV in the export, and the SQLite table it becomes."""

    name: str
    columns: tuple[str, ...]
    indexes: tuple[tuple[str, ...], ...] = ()

    @property
    def url(self) -> str:
        return f"{base_url()}/{self.name}.csv"


# Ordered as the specification orders them, so a diff against the workbook is
# readable. Column names are the export's own: `M`, `T`, `Sv`, `A`, `AP`, `D`
# and the rest are what the datasheet calls them, and renaming them to please
# a linter would make every query harder to check against the source.
TABLES: tuple[Table, ...] = (
    Table("Factions", ("id", "name", "link")),
    Table(
        "Source",
        ("id", "name", "type", "edition", "version", "errata_date", "errata_link"),
    ),
    Table(
        "Datasheets",
        (
            "id",
            "name",
            "faction_id",
            "source_id",
            "legend",
            "role",
            "loadout",
            "transport",
            "virtual",
            "is_support",
            "leader_head",
            "leader_footer",
            "damaged_w",
            "damaged_description",
            "link",
        ),
        indexes=(("faction_id",), ("name",)),
    ),
    Table(
        "Datasheets_abilities",
        (
            "datasheet_id",
            "line",
            "ability_id",
            "model",
            "name",
            "description",
            "type",
            "parameter",
        ),
        indexes=(("datasheet_id",),),
    ),
    Table(
        "Datasheets_keywords",
        ("datasheet_id", "keyword", "model", "is_faction_keyword"),
        indexes=(("datasheet_id",), ("keyword",)),
    ),
    Table(
        "Datasheets_models",
        (
            "datasheet_id",
            "line",
            "name",
            "M",
            "T",
            "Sv",
            "inv_sv",
            "inv_sv_descr",
            "W",
            "Ld",
            "OC",
            "base_size",
            "base_size_descr",
        ),
        indexes=(("datasheet_id",),),
    ),
    Table(
        "Datasheets_options",
        ("datasheet_id", "line", "button", "description"),
        indexes=(("datasheet_id",),),
    ),
    Table(
        "Datasheets_wargear",
        (
            "datasheet_id",
            "line",
            "line_in_wargear",
            "dice",
            "name",
            "description",
            "range",
            "type",
            "A",
            "BS_WS",
            "S",
            "AP",
            "D",
        ),
        indexes=(("datasheet_id",),),
    ),
    Table(
        "Datasheets_unit_composition",
        ("datasheet_id", "line", "description"),
        indexes=(("datasheet_id",),),
    ),
    Table(
        "Datasheets_models_cost",
        ("datasheet_id", "line", "description", "cost"),
        indexes=(("datasheet_id",),),
    ),
    Table(
        "Datasheets_stratagems",
        ("datasheet_id", "stratagem_id"),
        indexes=(("datasheet_id",), ("stratagem_id",)),
    ),
    Table(
        "Datasheets_enhancements",
        ("datasheet_id", "enhancement_id"),
        indexes=(("datasheet_id",), ("enhancement_id",)),
    ),
    Table(
        "Datasheets_detachment_abilities",
        ("datasheet_id", "detachment_ability_id"),
        indexes=(("datasheet_id",),),
    ),
    Table(
        "Datasheets_leader",
        ("leader_id", "attached_id"),
        indexes=(("leader_id",), ("attached_id",)),
    ),
    Table(
        "Stratagems",
        (
            "faction_id",
            "name",
            "id",
            "type",
            "cp_cost",
            "legend",
            "turn",
            "phase",
            "detachment",
            "detachment_id",
            "description",
        ),
        indexes=(("faction_id",), ("detachment_id",)),
    ),
    Table("Abilities", ("id", "name", "legend", "faction_id", "description")),
    Table(
        "Enhancements",
        (
            "faction_id",
            "name",
            "id",
            "cost",
            "detachment",
            "detachment_id",
            "upgrade",
            "legend",
            "description",
            "support_leader",
        ),
        indexes=(("faction_id",), ("detachment_id",)),
    ),
    Table(
        "Detachment_abilities",
        (
            "id",
            "faction_id",
            "name",
            "legend",
            "description",
            "detachment",
            "detachment_id",
        ),
        indexes=(("detachment_id",),),
    ),
    Table(
        "Detachments",
        ("id", "faction_id", "name", "legend", "type", "dp", "force_disposition"),
        indexes=(("faction_id",),),
    ),
    Table(
        "Detachments_chapter_dp",
        ("detachment_id", "keyword", "dp"),
        indexes=(("detachment_id",),),
    ),
    Table("Last_update", ("last_update",)),
)

TABLES_BY_NAME = {table.name: table for table in TABLES}


def data_tables() -> tuple[Table, ...]:
    """Every table except the update marker, which is metadata about the rest."""
    return tuple(t for t in TABLES if t.name != UPDATE_MARKER)


def marker_table() -> Table:
    return TABLES_BY_NAME[UPDATE_MARKER]
