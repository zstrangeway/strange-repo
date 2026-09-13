"""Working out what a unit costs, which is not a column.

``Datasheets_models_cost`` is a flattened rendering of the table printed on
the datasheet, not a price list. Rows whose ``cost`` is empty are section
headers and the value rows beneath one belong to it until the next header.
Reading the table as ``datasheet -> cost`` gets the right answer for the 989
datasheets that have one price and the wrong answer for the other 669.

Three kinds of section appear:

* An ordinal tier — "YOUR 1ST TO 2ND UNITS COST", then "YOUR 3RD + UNIT
  COSTS". Eleventh edition charges by how many of a datasheet the army
  already holds, so the third of something can cost more than the first.
  1st/2nd+ and 1st-to-3rd/4th+ shapes appear too.
* Priced wargear — "WARGEAR OPTIONS", then rows like "per Multi-melta".
* A variant of the whole datasheet, which only Agents of the Imperium use:
  the same unit priced once as part of an AGENTS detachment and again as an
  Assigned Agent, each with its own tiers underneath.

So a datasheet has no single price, and anything returning one number is
wrong about 40% of the roster.
"""

import re
from dataclasses import dataclass, field

# "YOUR 1ST TO 2ND UNITS COST", "YOUR 3RD + UNIT COSTS", "YOUR UNIT COSTS".
_TIER = re.compile(
    r"^YOUR\s+(?:(?P<first>\d+)(?:ST|ND|RD|TH)\s*"
    r"(?:TO\s+(?P<last>\d+)(?:ST|ND|RD|TH)\s*|(?P<open>\+)\s*)?)?"
    r"UNITS?\s+COSTS?$",
    re.IGNORECASE,
)
_WARGEAR_SECTION = re.compile(r"^WARGEAR\s+OPTIONS$", re.IGNORECASE)
# A trailing note on some datasheets, not a section with rows under it.
_NOTE = re.compile(r"^WARGEAR\s+COSTS\s+REMOVED$", re.IGNORECASE)
# The Agents of the Imperium variant headers are the only HTML in this table.
_VARIANT = re.compile(r"<div[^>]*>(?P<name>.*?)</div>", re.IGNORECASE | re.DOTALL)
# "10 models", "1 model", "10 Gretchin", "3 Wolf Guard Headtakers, 3 Hunting
# Wolves" — the count creed prices by is the leading integer where there is
# one.
_LEADING_COUNT = re.compile(r"^\s*(?P<count>\d+)\b")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _clean(text: str | None) -> str:
    """Costs arrive with leading spaces and some descriptions carry comments."""
    return _HTML_COMMENT.sub("", (text or "")).strip()


@dataclass(frozen=True)
class Option:
    """One priced line: a unit size, or a piece of wargear."""

    description: str
    cost: int
    models: int | None = None

    @property
    def is_per_item(self) -> bool:
        return self.description.lower().startswith("per ")


@dataclass
class Tier:
    """A price band, by how many of this datasheet the army already holds."""

    first: int = 1
    last: int | None = None
    options: list[Option] = field(default_factory=list)

    def covers(self, ordinal: int) -> bool:
        if ordinal < self.first:
            return False
        return self.last is None or ordinal <= self.last

    @property
    def label(self) -> str:
        if self.first == 1 and self.last is None:
            return "any"
        if self.last is None:
            return f"{self.first}+"
        if self.first == self.last:
            return str(self.first)
        return f"{self.first}-{self.last}"


@dataclass
class Variant:
    """A whole priced version of the datasheet. Usually there is exactly one."""

    name: str | None = None
    tiers: list[Tier] = field(default_factory=list)


@dataclass
class Pricing:
    """Everything the cost table says about one datasheet."""

    variants: list[Variant] = field(default_factory=list)
    wargear: list[Option] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def tiers(self) -> list[Tier]:
        """The default variant's tiers, which is what "the" price means."""
        return self.variants[0].tiers if self.variants else []

    @property
    def escalates(self) -> bool:
        """True when what the unit costs depends on how many you have taken."""
        return len(self.tiers) > 1

    @property
    def sizes(self) -> list[int]:
        """The model counts this datasheet can be taken at."""
        counts = {
            option.models
            for tier in self.tiers
            for option in tier.options
            if option.models is not None
        }
        return sorted(counts)

    def tier_for(self, ordinal: int) -> Tier | None:
        for tier in self.tiers:
            if tier.covers(ordinal):
                return tier
        return self.tiers[-1] if self.tiers else None

    def cost_for(self, models: int, ordinal: int = 1) -> int | None:
        """What the ordinal-th unit of this datasheet costs at this size.

        ``None`` rather than a guess when the size is not one the datasheet
        comes in: a number invented here would be indistinguishable from a
        real one everywhere downstream.
        """
        tier = self.tier_for(ordinal)
        if tier is None:
            return None
        for option in tier.options:
            if option.models == models:
                return option.cost
        return None

    def wargear_cost(self, description: str) -> int | None:
        wanted = description.strip().lower()
        for option in self.wargear:
            if option.description.strip().lower() == wanted:
                return option.cost
        return None


def parse(rows) -> Pricing:
    """Read one datasheet's cost rows, in the order the export gives them.

    ``rows`` are mappings with ``line``, ``description`` and ``cost``. Order is
    everything — a value row means nothing except in terms of the header above
    it — so they are sorted by line number rather than trusted to arrive
    sorted.
    """
    ordered = sorted(rows, key=lambda row: int(row["line"] or 0))
    pricing = Pricing()
    variant: Variant | None = None
    tier: Tier | None = None
    in_wargear = False

    for row in ordered:
        description = _clean(row["description"])
        cost = _clean(row["cost"])
        if not description:
            continue

        if not cost:
            match = _VARIANT.search(description)
            if match:
                variant = Variant(name=_clean(match.group("name")) or None)
                pricing.variants.append(variant)
                tier = None
                in_wargear = False
                continue
            if _WARGEAR_SECTION.match(description):
                in_wargear = True
                tier = None
                continue
            if _NOTE.match(description):
                pricing.notes.append(description)
                continue
            match = _TIER.match(description)
            if match:
                in_wargear = False
                first = int(match.group("first") or 1)
                last = int(match.group("last")) if match.group("last") else None
                # "YOUR 1ST UNIT COSTS" with no "+" and no "TO" is that one
                # unit only; "YOUR UNIT COSTS" with no ordinal at all is every
                # unit.
                if last is None and match.group("first") and not match.group("open"):
                    last = first
                tier = Tier(first=first, last=last)
                if variant is None:
                    variant = Variant()
                    pricing.variants.append(variant)
                variant.tiers.append(tier)
                continue
            # A header creed does not recognise. Kept rather than dropped, so
            # a shape added upstream shows up instead of silently mispricing.
            pricing.notes.append(description)
            continue

        value = int(cost) if cost.lstrip("-").isdigit() else None
        if value is None:
            pricing.notes.append(f"{description}: {cost}")
            continue
        count = _LEADING_COUNT.match(description)
        option = Option(
            description=description,
            cost=value,
            models=int(count.group("count")) if count else None,
        )
        if in_wargear:
            pricing.wargear.append(option)
        else:
            if tier is None:
                tier = Tier()
                if variant is None:
                    variant = Variant()
                    pricing.variants.append(variant)
                variant.tiers.append(tier)
            tier.options.append(option)

    return pricing
