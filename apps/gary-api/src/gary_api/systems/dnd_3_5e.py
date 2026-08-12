from gary_api.systems.base import (
    POINT_BUY,
    ROLL_4D6,
    Module,
    TwoDegrees,
)


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
    # No standard array: that is a fifth edition idea, and this edition's own
    # book offers rolling and a point buy. Adding it here would be a house
    # rule gary imposed on every 3.5 table.
    offers = (ROLL_4D6, POINT_BUY)
    hit_dice = {
        "barbarian": 12,
        "fighter": 10, "paladin": 10, "ranger": 10,
        "cleric": 8, "druid": 8, "monk": 8,
        "bard": 6, "rogue": 6,
        "sorcerer": 4, "wizard": 4,
    }
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
            hook=(
                "The company is paying you by the day to get down the "
                "shaft and report what the seam has become. The families "
                "waiting at the winding-house have paid you nothing and "
                "want their dead brought up, and both sides expect to hear "
                "your answer first."
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
            hook=(
                "You are carrying the deed. The heir who inherited the "
                "hall has never seen it, does not intend to, and has hired "
                "you to take possession, pay off the staff and sell the "
                "place by the end of the month. Nobody mentioned the staff "
                "having stayed eleven years without wages."
            ),
            opening="the carriage drive, in sight of the hall's lit windows",
        ),
    )
