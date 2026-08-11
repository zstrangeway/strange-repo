from gary_api.systems.base import FourDegrees, Module


class Pathfinder2e(FourDegrees):
    """The one system here that grades four ways.

    It is registered alongside three that grade two, and nothing outside this
    package notices the difference — which is the whole argument for the rules
    living behind an interface rather than in a paragraph of prompt.
    """

    slug = "pathfinder-2e"
    name = "Pathfinder 2nd Edition"
    blurb = (
        "Three actions a turn, and four degrees of success on every check — "
        "critical success at ten over, critical failure at ten under. Say which "
        "degree was reached and what it costs; a plain success and a critical "
        "one should not read the same."
    )
    classes = (
        "alchemist", "barbarian", "bard", "champion", "cleric", "druid",
        "fighter", "investigator", "monk", "oracle", "ranger", "rogue",
        "sorcerer", "swashbuckler", "witch", "wizard",
    )
    modules = (
        Module(
            slug="salt-and-cinder",
            title="Salt and Cinder",
            premise=(
                "The island's only harbour is silting up with ash, and the "
                "mountain has not erupted. Something is burning underneath it, "
                "methodically, and the ash is coming up warm and smelling of a "
                "spice nobody trades in."
            ),
            hook=(
                "The harbourmaster is losing a berth a week to the ash and "
                "has hired you to find where it is coming from, before the "
                "traders stop calling and Otari stops eating. The last "
                "surveyor sent down came back and will not talk about it."
            ),
            opening="the ash-choked quay at Otari harbour",
        ),
        Module(
            slug="the-quiet-census",
            title="The Quiet Census",
            premise=(
                "Every person in Otari has been counted, twice, by someone "
                "nobody hired and nobody can describe afterwards. The second "
                "count came back one higher than the first."
            ),
            hook=(
                "The town council wants to know who did the counting and "
                "who the extra person is, quietly, before the news gets "
                "out and Otari starts deciding for itself. You have the "
                "second list. Somebody on it should not be."
            ),
            opening="the market square, the morning after the second count",
        ),
    )
