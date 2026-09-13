"""Turning results into the text a person or a model reads.

One place, used by both surfaces, so the command line and the MCP server
cannot drift into describing the same datasheet differently.

Every rendering ends with where the data came from and when. A model reading a
tool result cannot see the sync log, and without the date in the text it has
no way to tell somebody how current the answer is.
"""

from . import export


def provenance_block(provenance) -> str:
    lines = [f"Data as of {provenance.last_update}."]
    lines += provenance.warnings
    lines.append(export.ATTRIBUTION)
    return "\n".join(lines)


def _statline(model: dict) -> str:
    invulnerable = (
        f" | Invuln {model['invulnerable']}+" if model["invulnerable"] else ""
    )
    return (
        f"M {model['M']} | T {model['T']} | Sv {model['Sv']}{invulnerable} | "
        f"W {model['W']} | Ld {model['Ld']} | OC {model['OC']}"
    )


def datasheet(sheet, provenance) -> str:
    heading = sheet.faction + (f" — {sheet.role}" if sheet.role else "")
    out = [f"# {sheet.name}", heading]
    if sheet.virtual:
        out.append(
            "_This datasheet cannot be taken in an army list; it only enters "
            "play by being summoned._"
        )

    out.append("\n## Statlines")
    for model in sheet.models:
        out.append(f"- **{model['name']}** — {_statline(model)}")
        if model["invulnerable_note"]:
            out.append(f"  - {model['invulnerable_note']}")

    if sheet.composition:
        out.append("\n## Unit composition")
        out += [f"- {line}" for line in sheet.composition]

    if sheet.wargear:
        out.append("\n## Weapons")
        for gear in sheet.wargear:
            kind = gear["type"] or ""
            # The export stores a ranged weapon's range as a bare number. Left
            # as-is it reads as a stat rather than a distance in inches.
            span = gear["range"] or ""
            if span and span.strip().isdigit():
                span = f'{span}"'
            out.append(
                f"- **{gear['name']}** ({kind}) — Range {span}, "
                f"A {gear['A']}, {'WS' if kind == 'Melee' else 'BS'} "
                f"{gear['BS_WS']}, S {gear['S']}, AP {gear['AP']}, D {gear['D']}"
            )
            if gear["profile"]:
                out.append(f"  - {gear['profile']}")

    if sheet.abilities:
        out.append("\n## Abilities")
        for ability in sheet.abilities:
            head = ability["name"] or ""
            if ability["parameter"]:
                head += f" {ability['parameter']}"
            out.append(f"- **{head}**")
            if ability["description"]:
                body = ability["description"].replace("\n", "\n  ")
                out.append(f"  {body}")

    if sheet.damaged:
        out.append("\n## Damaged")
        out.append(f"At {sheet.damaged['wounds']} wounds: {sheet.damaged['effect']}")

    if sheet.leads:
        out.append("\n## Can lead")
        out.append(", ".join(led["name"] for led in sheet.leads))
    if sheet.led_by:
        out.append("\n## Can be led by")
        out.append(", ".join(leader["name"] for leader in sheet.led_by))

    out.append("\n## Points")
    out.append(points_block(sheet.points))

    if sheet.keywords:
        out.append("\n**Keywords:** " + ", ".join(sheet.keywords))
    if sheet.faction_keywords:
        out.append("**Faction keywords:** " + ", ".join(sheet.faction_keywords))
    if sheet.link:
        out.append(f"\n{sheet.link}")
    out.append("\n" + provenance_block(provenance))
    return "\n".join(out)


def points_block(pricing) -> str:
    """Points as the table actually works, never as a single number."""
    lines = []
    for variant in pricing.variants:
        if variant.name:
            lines.append(f"_{variant.name}_")
        for tier in variant.tiers:
            sizes = ", ".join(
                f"{option.description} = {option.cost}pts" for option in tier.options
            )
            if tier.label == "any":
                lines.append(f"- {sizes}")
            else:
                lines.append(f"- your {tier.label} unit(s) of this datasheet: {sizes}")
    if pricing.escalates:
        lines.append(
            "_This unit's cost depends on how many of it your army already "
            "has, so there is no single price._"
        )
    if pricing.wargear:
        lines.append("\nWargear options:")
        lines += [
            f"- {option.description} = {option.cost}pts" for option in pricing.wargear
        ]
    for note in pricing.notes:
        lines.append(f"_{note}_")
    return "\n".join(lines) or "_no points in the export for this datasheet_"


def search_results(result, provenance) -> str:
    if not result.matches:
        return f"Nothing matched {result.query!r}.\n\n" + provenance_block(provenance)
    out = [f"{result.total} datasheet(s) matched {result.query!r}."]
    if result.truncated:
        out.append(
            f"Showing the first {len(result.matches)}. Narrow it with a longer "
            "name or a faction."
        )
    out.append("")
    for match in result.matches:
        role = f" — {match.role}" if match.role else ""
        out.append(f"- **{match.name}** ({match.faction}){role} `{match.id}`")
    out.append("\n" + provenance_block(provenance))
    return "\n".join(out)


def stratagems(found, provenance, heading: str = "Stratagems") -> str:
    if not found:
        return f"No stratagems matched.\n\n{provenance_block(provenance)}"
    out = [f"# {heading} ({len(found)})", ""]
    for stratagem in found:
        cost = f"{stratagem.cp}CP" if stratagem.cp is not None else "—"
        where = stratagem.detachment or stratagem.faction_id or "Core"
        out.append(f"## {stratagem.name} — {cost} ({where})")
        if stratagem.turn or stratagem.phase:
            out.append(
                f"_{stratagem.turn or 'either turn'}, {stratagem.phase or 'any phase'}_"
            )
        out.append(stratagem.description)
        out.append("")
    out.append(provenance_block(provenance))
    return "\n".join(out)


def detachment(one, contents, provenance) -> str:
    out = [f"# {one.name}", f"{one.faction}"]
    if one.dp is not None:
        out.append(f"**Detachment Points:** {one.dp}")
    if one.dp_varies:
        out.append(
            "Detachment Points differ by chapter: "
            + ", ".join(f"{name} {value}" for name, value in one.chapter_dp.items())
            + f". Any chapter not listed uses {one.dp}."
        )
    if one.force_disposition:
        out.append(f"**Force Disposition:** {one.force_disposition}")
    if one.ability:
        out.append(f"\n## {one.ability['name']}")
        out.append(one.ability["description"])
    enhancements = contents.get("enhancements", [])
    if enhancements:
        out.append("\n## Enhancements")
        for enhancement in enhancements:
            out.append(f"- **{enhancement['name']}** — {enhancement['cost']}pts")
            if enhancement["eligibility"]:
                out.append(f"  {enhancement['eligibility']}")
    found = contents.get("stratagems", [])
    if found:
        out.append(f"\n## Stratagems ({len(found)})")
        for stratagem in found:
            cost = f"{stratagem.cp}CP" if stratagem.cp is not None else "—"
            out.append(f"- **{stratagem.name}** ({cost})")
    out.append("\n" + provenance_block(provenance))
    return "\n".join(out)


def army_list(priced, provenance) -> str:
    out = [f"# {priced.name}", f"{priced.faction_id} — {priced.points_limit} points"]
    if priced.detachment:
        detail = priced.detachment.name
        if priced.detachment.dp is not None:
            detail += f" ({priced.detachment.dp} DP"
            if priced.detachment.force_disposition:
                detail += f", {priced.detachment.force_disposition}"
            detail += ")"
        out.append(f"**Detachment:** {detail}")
    else:
        out.append("**Detachment:** none chosen")
    out.append("")
    for unit in priced.units:
        cost = "?" if unit.unit_cost is None else unit.unit_cost
        line = f"- **{unit.name}** — {unit.models} models — {cost}pts"
        if unit.tier and unit.tier != "any":
            line += f" (your {unit.tier} of this datasheet)"
        line += f"  `{unit.id}`"
        out.append(line)
        for gear in unit.wargear:
            out.append(
                f"  - {gear['quantity']}x {gear['description']} — "
                f"{gear['cost'] * gear['quantity']}pts"
            )
        if unit.enhancement:
            out.append(
                f"  - Enhancement: {unit.enhancement['name']} — "
                f"{unit.enhancement['cost']}pts"
            )
        if unit.missing_from_export:
            out.append("  - _this datasheet is no longer in the export_")
    out.append("")
    out.append(f"**Total:** {priced.total} / {priced.points_limit}")
    if priced.over_by:
        out.append(f"**Over by {priced.over_by} points.**")
    else:
        out.append(f"{priced.remaining} points remain.")
    out.append("\n" + provenance_block(provenance))
    return "\n".join(out)


def report(one, provenance) -> str:
    out = ["# List check", "", one.summary(), ""]
    if one.findings:
        out.append("## Problems")
        for finding in one.findings:
            where = f"**{finding.unit}**: " if finding.unit else ""
            out.append(f"- {where}{finding.problem}")
            out.append(f"  - {finding.fix}")
        out.append("")
    if one.checked:
        out.append("## Checked")
        out += [f"- {item}" for item in one.checked]
        out.append("")
    if one.unverified:
        out.append("## Shown but not decided")
        out.append(
            "These are written as prose in the export rather than as data, so "
            "creed cannot check them:"
        )
        out += [f"- {item}" for item in one.unverified]
        out.append("")
    out.append("## Not checked")
    out.append(
        "These are core rules and are not in the export at all. creed has no "
        "opinion on them, and a clean report above does not mean they pass:"
    )
    out += [f"- {item}" for item in one.unchecked]
    out.append("\n" + provenance_block(provenance))
    return "\n".join(out)


def attack_result(result, provenance) -> str:
    out = [f"# {result.weapon}"]
    if result.attacker or result.target:
        out.append(f"{result.attacker or '?'} into {result.target or '?'}")
    out.append("")
    out.append(f"- Attacks: {result.attacks:g}")
    for step in result.steps:
        value = "" if step.value is None else f" ({step.value:.0%})"
        out.append(f"- {step.detail}{value}")
    out.append("")
    out.append(f"- Expected hits: {result.expected_hits:.2f}")
    out.append(f"- Expected wounds: {result.expected_wounds:.2f}")
    out.append(f"- Expected unsaved: {result.expected_unsaved:.2f}")
    out.append(f"- **Expected damage: {result.expected_damage:.2f}**")
    out.append(f"- **Expected models killed: {result.expected_kills:.2f}**")
    if result.applied:
        out.append("\n**Applied:** " + ", ".join(result.applied))
    if result.not_applied:
        out.append(
            "\n**Not applied** — creed did not model these, so the numbers "
            "above are without them:"
        )
        out += [f"- {ability}" for ability in result.not_applied]
    if result.notes:
        out += ["", *[f"_{note}_" for note in result.notes]]
    out.append("\n" + provenance_block(provenance))
    return "\n".join(out)


__all__ = [
    "army_list",
    "attack_result",
    "datasheet",
    "detachment",
    "points_block",
    "provenance_block",
    "report",
    "search_results",
    "stratagems",
]
