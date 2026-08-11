from gary_api.systems.base import Module, TwoDegrees


class DnD35e(TwoDegrees):
    slug = "dnd-3-5e"
    name = "Dungeons & Dragons 3.5 Edition"
    blurb = (
        "A rule for everything and a modifier for every rule. Skill ranks, "
        "feats, attacks of opportunity and stacking bonuses all matter, and "
        "players expect their build to pay off. Be precise about numbers and "
        "say which modifiers you applied."
    )
    classes = (
        "barbarian", "bard", "cleric", "druid", "fighter", "monk",
        "paladin", "ranger", "rogue", "sorcerer", "wizard",
    )
    modules = (
        Module(
            slug="the-glass-mine",
            title="The Glass Mine",
            premise=(
                "The seam under Corvel turned to glass in a single night, with "
                "the shift still inside it. The company wants its tunnel back. "
                "The families want their dead back. Neither has asked what "
                "made the change."
            ),
            opening="the winding-house at the head of the Corvel shaft",
        ),
        Module(
            slug="shrike-hall",
            title="Shrike Hall",
            premise=(
                "A minor noble's hall, inherited by someone who has never seen "
                "it, and staffed by servants who have not been paid in eleven "
                "years and have not left. They are still keeping the house "
                "exactly as the old master liked it."
            ),
            opening="the carriage drive, in sight of the hall's lit windows",
        ),
    )
