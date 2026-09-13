"""A small export, built by hand, with numbers the scenarios can assert on.

The real export is 165,000 rows and changes under us — which is the point of
the app and exactly wrong for a spec. So the specs run against this: the same
twenty-one files, the same dialect (pipe-delimited, BOM, trailing delimiter,
records that end with a delimiter-newline), and a dozen rows whose every value
is known here.

It carries the shapes that were expensive to learn about the real thing:

* a description with a literal newline in it, and another with a 6" in it, so
  a spec fails if anybody reads this with the csv module again
* a unit priced by how many you have taken, alongside one priced flat
* priced wargear
* rules text as HTML, with a kwb keyword span and a div
"""

# Every record ends with the delimiter, then a newline. See sync._records.
BOM = "﻿"


def table(header, rows):
    lines = ["|".join(header) + "|"]
    lines += ["|".join(str(cell) for cell in row) + "|" for row in rows]
    return BOM + "\n".join(lines) + "\n"


# Two factions, four datasheets. Names are invented so that nothing here can
# pass by accidentally matching the real export.
FACTIONS = table(
    ["id", "name", "link"],
    [
        ("TG", "Test Guard", "https://example.invalid/tg"),
        ("TX", "Test Xenos", "https://example.invalid/tx"),
    ],
)

SOURCE = table(
    ["id", "name", "type", "edition", "version", "errata_date", "errata_link"],
    [("S1", "Test Index", "Index", "11", "1.0", "01.01.2026 0:00:00", "")],
)

DATASHEETS = table(
    [
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
    ],
    [
        # A plain infantry unit, in two sizes, priced by how many you take.
        (
            "D1",
            "Testudo Guard",
            "TG",
            "S1",
            "They hold.",
            "",
            "",
            "",
            "false",
            "false",
            "",
            "",
            "",
            "",
            "https://example.invalid/d1",
        ),
        # A character who can lead D1.
        (
            "D2",
            "Testudo Captain",
            "TG",
            "S1",
            "He points.",
            "",
            "",
            "",
            "false",
            "false",
            "",
            "",
            "",
            "",
            "https://example.invalid/d2",
        ),
        # A vehicle with a damaged bracket, priced flat, with priced wargear.
        (
            "D3",
            "Testudo Walker",
            "TG",
            "S1",
            "It walks.",
            "",
            "",
            "",
            "false",
            "false",
            "",
            "",
            "4",
            "While this model has 1-4 wounds remaining, "
            "subtract 2 from its Objective Control.",
            "https://example.invalid/d3",
        ),
        # A datasheet that cannot be taken in a list at all.
        (
            "D4",
            "Testudo Spawn",
            "TG",
            "S1",
            "It arrives uninvited.",
            "",
            "",
            "",
            "true",
            "false",
            "",
            "",
            "",
            "",
            "https://example.invalid/d4",
        ),
        # Another faction's unit, for the wrong-faction check. Shares a name
        # with D1 on purpose, so "by name" has to be ambiguous.
        (
            "D5",
            "Testudo Guard",
            "TX",
            "S1",
            "They also hold.",
            "",
            "",
            "",
            "false",
            "false",
            "",
            "",
            "",
            "",
            "https://example.invalid/d5",
        ),
    ],
)

# One shared ability by reference, one written on the datasheet, and one whose
# text contains a literal newline and an inches mark.
ABILITIES = table(
    ["id", "name", "legend", "faction_id", "description"],
    [
        (
            "A1",
            "Testudo Resolve",
            "",
            "TG",
            '<div class="abName">TESTUDO RESOLVE'
            '<span class="h_number">26.01</span></div>'
            '<p>While a <span class="kwb">TESTUDO</span> unit is within 6" of\n'
            "one or more friendly models, it is steady.</p>"
            "<ul><li>Add 1 to its Leadership.</li><li>Add 1 to its OC.</li></ul>",
        )
    ],
)

DATASHEETS_ABILITIES = table(
    [
        "datasheet_id",
        "line",
        "ability_id",
        "model",
        "name",
        "description",
        "type",
        "parameter",
    ],
    [
        ("D1", "1", "A1", "", "", "", "", ""),
        (
            "D1",
            "2",
            "",
            "",
            "Shield Wall",
            "<b>Each time</b> an attack targets "
            "this unit, subtract 1 from the Hit roll.",
            "",
            "",
        ),
        ("D3", "1", "", "", "Steady Tread", "It does not slow down.", "", ""),
    ],
)

DATASHEETS_KEYWORDS = table(
    ["datasheet_id", "keyword", "model", "is_faction_keyword"],
    [
        ("D1", "Infantry", "", "false"),
        ("D1", "Battleline", "", "false"),
        ("D1", "Testudo", "", "false"),
        ("D1", "Test Guard", "", "true"),
        ("D2", "Infantry", "", "false"),
        ("D2", "Character", "", "false"),
        ("D2", "Test Guard", "", "true"),
        ("D3", "Vehicle", "", "false"),
        ("D3", "Test Guard", "", "true"),
        ("D4", "Infantry", "", "false"),
        ("D4", "Test Guard", "", "true"),
        ("D5", "Infantry", "", "false"),
        ("D5", "Test Xenos", "", "true"),
    ],
)

# D1 has two profiles, so a spec can check that both come back.
DATASHEETS_MODELS = table(
    [
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
    ],
    [
        (
            "D1",
            "1",
            "Testudo Guard",
            '6"',
            "4",
            "3+",
            "",
            "",
            "2",
            "6+",
            "2",
            "32mm",
            "",
        ),
        (
            "D1",
            "2",
            "Testudo Sergeant",
            '6"',
            "4",
            "3+",
            "5",
            "",
            "3",
            "6+",
            "2",
            "32mm",
            "",
        ),
        (
            "D2",
            "1",
            "Testudo Captain",
            '6"',
            "4",
            "3+",
            "4",
            "",
            "5",
            "6+",
            "1",
            "40mm",
            "",
        ),
        (
            "D3",
            "1",
            "Testudo Walker",
            '8"',
            "9",
            "2+",
            "",
            "",
            "12",
            "7+",
            "3",
            "80mm",
            "",
        ),
        (
            "D4",
            "1",
            "Testudo Spawn",
            '7"',
            "5",
            "5+",
            "",
            "",
            "4",
            "8+",
            "1",
            "50mm",
            "",
        ),
        (
            "D5",
            "1",
            "Testudo Guard",
            '6"',
            "5",
            "4+",
            "",
            "",
            "2",
            "6+",
            "2",
            "32mm",
            "",
        ),
    ],
)

DATASHEETS_WARGEAR = table(
    [
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
    ],
    [
        # Plain, and the numbers the math scenarios use.
        (
            "D1",
            "1",
            "1",
            "",
            "Test rifle",
            "",
            "24",
            "Ranged",
            "2",
            "3",
            "4",
            "-1",
            "1",
        ),
        # Sustained Hits, unconditional.
        (
            "D1",
            "2",
            "1",
            "",
            "Test stormgun",
            "SUSTAINED HITS 1",
            "18",
            "Ranged",
            "2",
            "3",
            "4",
            "-1",
            "1",
        ),
        # Conditional Lethal Hits: creed must refuse to apply it.
        (
            "D1",
            "3",
            "1",
            "",
            "Test lance",
            "LETHAL HITS: non-VEHICLE",
            "12",
            "Ranged",
            "1",
            "3",
            "6",
            "-2",
            "2",
        ),
        # An ability creed does not model at all.
        (
            "D1",
            "4",
            "1",
            "",
            "Test flail",
            "CLEAVE 2",
            "Melee",
            "Melee",
            "3",
            "3",
            "4",
            "0",
            "1",
        ),
        (
            "D2",
            "1",
            "1",
            "",
            "Test blade",
            "",
            "Melee",
            "Melee",
            "4",
            "2",
            "5",
            "-2",
            "2",
        ),
        # Torrent, and a dice-expression damage.
        (
            "D3",
            "1",
            "1",
            "",
            "Test flamer",
            "TORRENT",
            "12",
            "Ranged",
            "D6",
            "",
            "5",
            "-1",
            "D3",
        ),
    ],
)

DATASHEETS_UNIT_COMPOSITION = table(
    ["datasheet_id", "line", "description"],
    [
        ("D1", "1", "1 Testudo Sergeant"),
        ("D1", "2", "4-9 Testudo Guard"),
        ("D2", "1", "1 Testudo Captain"),
        ("D3", "1", "1 Testudo Walker"),
        ("D4", "1", "1 Testudo Spawn"),
        ("D5", "1", "5 Testudo Guard"),
    ],
)

DATASHEETS_OPTIONS = table(
    ["datasheet_id", "line", "button", "description"],
    [("D1", "1", "•", "Any model's Test rifle can be replaced with 1 Test flail.")],
)

# The shape that matters most. D1 escalates and has priced wargear; D3 is flat.
DATASHEETS_MODELS_COST = table(
    ["datasheet_id", "line", "description", "cost"],
    [
        ("D1", "1", "YOUR 1ST TO 2ND UNITS COST", ""),
        ("D1", "2", "5 models", " 100"),
        ("D1", "3", "10 models", "200"),
        ("D1", "4", "YOUR 3RD + UNIT COSTS", ""),
        ("D1", "5", "5 models", "120"),
        ("D1", "6", "10 models", "240"),
        ("D1", "7", "WARGEAR OPTIONS", ""),
        ("D1", "8", "per Test flail", "5"),
        ("D2", "1", "YOUR UNIT COSTS", ""),
        ("D2", "2", "1 model", "80"),
        ("D3", "1", "YOUR UNIT COSTS", ""),
        ("D3", "2", "1 model", "150"),
        ("D4", "1", "YOUR UNIT COSTS", ""),
        ("D4", "2", "1 model", "60"),
        ("D5", "1", "YOUR UNIT COSTS", ""),
        ("D5", "2", "5 models", "90"),
    ],
)

DETACHMENTS = table(
    ["id", "faction_id", "name", "legend", "type", "dp", "force_disposition"],
    [
        ("DT1", "TG", "Shield Doctrine", "", "", "2", "Take and Hold"),
        ("DT2", "TG", "Spear Doctrine", "", "", "3", "Purge the Foe"),
        ("DT3", "TX", "Alien Doctrine", "", "", "1", "Reconnaissance"),
    ],
)

# DT2's points differ by chapter; DT1's do not.
DETACHMENTS_CHAPTER_DP = table(
    ["detachment_id", "keyword", "dp"],
    [("DT2", "First Company", "4"), ("DT2", "Second Company", "2")],
)

DETACHMENT_ABILITIES = table(
    [
        "id",
        "faction_id",
        "name",
        "legend",
        "description",
        "detachment",
        "detachment_id",
    ],
    [
        (
            "DA1",
            "TG",
            "Hold The Line",
            "",
            "Units in this detachment are <b>steady</b>.",
            "Shield Doctrine",
            "DT1",
        ),
        (
            "DA2",
            "TG",
            "Press The Attack",
            "",
            "Units strike first.",
            "Spear Doctrine",
            "DT2",
        ),
    ],
)

DATASHEETS_DETACHMENT_ABILITIES = table(
    ["datasheet_id", "detachment_ability_id"], [("D1", "DA1"), ("D2", "DA1")]
)

STRATAGEMS = table(
    [
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
    ],
    [
        (
            "TG",
            "BRACE",
            "ST1",
            "Battle Tactic",
            "1",
            "",
            "Your turn",
            "Shooting phase",
            "Shield Doctrine",
            "DT1",
            "<b>WHEN:</b> Your Shooting phase.<br><b>EFFECT:</b> Nothing moves.",
        ),
        (
            "TG",
            "COUNTERCHARGE",
            "ST2",
            "Battle Tactic",
            "2",
            "",
            "Opponent's turn",
            "Charge phase",
            "Shield Doctrine",
            "DT1",
            "<b>WHEN:</b> Your opponent's Charge phase.",
        ),
        (
            "TG",
            "SPEARHEAD",
            "ST3",
            "Battle Tactic",
            "1",
            "",
            "Your turn",
            "Movement phase",
            "Spear Doctrine",
            "DT2",
            "Move faster.",
        ),
        # A core stratagem: no faction, no detachment, no turn, no phase. It
        # must match every filter rather than none.
        (
            "",
            "COMMAND RE-ROLL",
            "ST4",
            "Core",
            "1",
            "",
            "",
            "",
            "",
            "",
            "Re-roll one dice.",
        ),
    ],
)

DATASHEETS_STRATAGEMS = table(
    ["datasheet_id", "stratagem_id"], [("D1", "ST1"), ("D1", "ST4")]
)

ENHANCEMENTS = table(
    [
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
    ],
    [
        (
            "TG",
            "Bulwark",
            "EN1",
            "15",
            "Shield Doctrine",
            "DT1",
            "false",
            "",
            '<span class="kwb">TEST GUARD</span> model only. Improves the save.',
            "false",
        ),
        (
            "TG",
            "Spearpoint",
            "EN2",
            "20",
            "Spear Doctrine",
            "DT2",
            "false",
            "",
            "Adds an attack.",
            "false",
        ),
    ],
)

DATASHEETS_ENHANCEMENTS = table(
    ["datasheet_id", "enhancement_id"], [("D2", "EN1"), ("D2", "EN2")]
)

DATASHEETS_LEADER = table(["leader_id", "attached_id"], [("D2", "D1")])


def build(last_update: str = "2026-01-01 00:00:00") -> dict[str, str]:
    """Every table, keyed by the name the export uses."""
    return {
        "Factions": FACTIONS,
        "Source": SOURCE,
        "Datasheets": DATASHEETS,
        "Datasheets_abilities": DATASHEETS_ABILITIES,
        "Datasheets_keywords": DATASHEETS_KEYWORDS,
        "Datasheets_models": DATASHEETS_MODELS,
        "Datasheets_options": DATASHEETS_OPTIONS,
        "Datasheets_wargear": DATASHEETS_WARGEAR,
        "Datasheets_unit_composition": DATASHEETS_UNIT_COMPOSITION,
        "Datasheets_models_cost": DATASHEETS_MODELS_COST,
        "Datasheets_stratagems": DATASHEETS_STRATAGEMS,
        "Datasheets_enhancements": DATASHEETS_ENHANCEMENTS,
        "Datasheets_detachment_abilities": DATASHEETS_DETACHMENT_ABILITIES,
        "Datasheets_leader": DATASHEETS_LEADER,
        "Stratagems": STRATAGEMS,
        "Abilities": ABILITIES,
        "Enhancements": ENHANCEMENTS,
        "Detachment_abilities": DETACHMENT_ABILITIES,
        "Detachments": DETACHMENTS,
        "Detachments_chapter_dp": DETACHMENTS_CHAPTER_DP,
        "Last_update": table(["last_update"], [(last_update,)]),
    }
