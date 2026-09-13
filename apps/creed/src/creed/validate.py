"""Checking a list, and being honest about what checking means.

This is the module with the most room to do harm, because its failure mode is
not an error — it is a clean report on a list that is illegal, which somebody
finds out about at a tournament.

The export encodes three different kinds of constraint and creed treats them
differently on purpose:

* Structural. Who can lead whom, which detachment an enhancement belongs to,
  whether a datasheet can be taken at all, what faction a unit is. These are
  columns and join tables, so they are checked.
* Prose. An enhancement's eligibility reads "ADEPTUS CUSTODES model only" — a
  sentence in a description field, not a field of its own. creed shows it and
  says it has not decided it.
* Absent. How many of one datasheet an army may take, battleline minimums,
  what a Warlord must be. These are core rules and appear nowhere in these
  tables. creed names them as unchecked rather than letting a clean report
  imply they passed.

So creed never reports a list as legal. It reports what it checked.
"""

from dataclasses import dataclass, field

from . import army, datasheets

# Named one by one rather than as "and others", because a vague disclaimer is
# read as boilerplate and skipped, and the whole point is that somebody knows
# which rules they still have to check themselves.
UNCHECKED_RULES = (
    "how many times one datasheet may be taken (the Rule of Three and its exceptions)",
    "Battleline and other minimum requirements for the detachment",
    "Warlord selection, and whether one is required",
    "Epic Hero uniqueness across the army",
    "transport capacity against what is embarked",
    "wargear options against what the datasheet actually allows",
    "anything printed in a rulebook rather than on a datasheet",
)


@dataclass
class Finding:
    """One thing wrong, and what would fix it."""

    unit: str | None
    problem: str
    fix: str


@dataclass
class Report:
    checked: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)
    unchecked: tuple[str, ...] = UNCHECKED_RULES
    empty: bool = False

    @property
    def passed(self) -> bool:
        """Nothing creed can see is wrong. Deliberately not called `legal`."""
        return not self.findings and not self.empty

    def summary(self) -> str:
        if self.empty:
            return "This list has no units in it, so there was nothing to check."
        if self.findings:
            return f"{len(self.findings)} problem(s) found."
        return (
            "Nothing creed can check is wrong with this list. That is not the "
            "same as the list being legal — see what was not checked."
        )


def check(connection, list_id: int) -> Report:
    priced = army.price(connection, list_id)
    report = Report()

    if not priced.units:
        report.empty = True
        return report

    report.checked.append("points against the limit")
    if priced.total > priced.points_limit:
        report.findings.append(
            Finding(
                unit=None,
                problem=(
                    f"the list is {priced.over_by} points over its "
                    f"{priced.points_limit} point limit"
                ),
                fix="remove or shrink a unit",
            )
        )

    report.checked.append("a detachment has been chosen")
    if priced.detachment is None:
        report.findings.append(
            Finding(
                unit=None,
                problem="no detachment has been chosen",
                fix="set one; it decides the stratagems and enhancements",
            )
        )

    report.checked.append("every unit belongs to the list's faction")
    report.checked.append("no unit is one that cannot be taken in a list")
    report.checked.append("attached characters can lead what they are attached to")
    report.checked.append("enhancements belong to the list's detachment")
    report.checked.append("enhancements are on characters")

    by_id = {unit.id: unit for unit in priced.units}

    for unit in priced.units:
        if unit.missing_from_export:
            report.findings.append(
                Finding(
                    unit=unit.name,
                    problem="this datasheet is no longer in the export",
                    fix="it may have been renamed or removed; check Wahapedia",
                )
            )
            continue

        sheet = datasheets.get(connection, unit.datasheet_id)

        if sheet.faction_id != priced.faction_id:
            report.findings.append(
                Finding(
                    unit=unit.name,
                    problem=(
                        f"belongs to {sheet.faction}, but this is a "
                        f"{priced.faction_id} list"
                    ),
                    fix="remove it, or start a list for its faction",
                )
            )

        if sheet.virtual:
            report.findings.append(
                Finding(
                    unit=unit.name,
                    problem="this datasheet cannot be taken in a list",
                    fix="it only enters play by being summoned; remove it",
                )
            )

        if unit.unit_cost is None:
            report.findings.append(
                Finding(
                    unit=unit.name,
                    problem=f"no price for {unit.models} models on this datasheet",
                    fix=(
                        "take it at a size it comes in: "
                        + ", ".join(str(size) for size in sheet.points.sizes)
                    ),
                )
            )

        if unit.attached_to is not None:
            target = by_id.get(unit.attached_to)
            can_lead = {led["id"] for led in sheet.leads}
            if target is not None and target.datasheet_id not in can_lead:
                names = [led["name"] for led in sheet.leads]
                report.findings.append(
                    Finding(
                        unit=unit.name,
                        problem=f"cannot lead {target.name}",
                        fix=(
                            "it can lead: " + ", ".join(names)
                            if names
                            else "this datasheet cannot lead anything"
                        ),
                    )
                )

        if unit.enhancement is not None:
            enhancement = unit.enhancement
            if priced.detachment is not None and enhancement["detachment_id"] not in (
                priced.detachment.id,
                "",
                None,
            ):
                report.findings.append(
                    Finding(
                        unit=unit.name,
                        problem=(
                            f"{enhancement['name']} belongs to a different detachment"
                        ),
                        fix=(
                            "it is from "
                            f"{enhancement['detachment_id']}; this list runs "
                            f"{priced.detachment.name}"
                        ),
                    )
                )
            if "Character" not in sheet.keywords:
                report.findings.append(
                    Finding(
                        unit=unit.name,
                        problem="is not a Character but carries an enhancement",
                        fix="move the enhancement to a Character",
                    )
                )
            # The eligibility wording is prose. creed carries it through and
            # says plainly that it did not decide it.
            if enhancement.get("eligibility"):
                report.unverified.append(
                    f"{unit.name}: {enhancement['name']} says "
                    f"“{_first_sentence(enhancement['eligibility'])}” "
                    "— creed has not checked that this unit qualifies"
                )

    return report


def _first_sentence(text: str) -> str:
    from .markup import to_markdown

    plain = to_markdown(text).replace("\n", " ").strip()
    for stop in (". ", "."):
        if stop in plain:
            return plain.split(stop)[0].strip()
    return plain[:160]
