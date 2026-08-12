from gary_api.systems.base import (
    POINT_BUY,
    ROLL_4D6,
    STANDARD_ARRAY,
    Module,
    TwoDegrees,
)


class DnD5e(TwoDegrees):
    slug = "dnd-5e"
    name = "Dungeons & Dragons 5th Edition"
    blurb = (
        "Roll a d20, add a modifier, meet a difficulty class. Advantage and "
        "disadvantage replace most fiddly bonuses. Rulings are lighter than the "
        "older editions and the game moves quickly; when a rule is unclear, "
        "favour the fiction and keep going."
    )
    classes = (
        "barbarian", "bard", "cleric", "druid", "fighter", "monk",
        "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard",
    )
    # All three are in the Player's Handbook: the array and point buy as the
    # ways to build one, and four dice dropping the lowest as the way to roll
    # one. Ordered gently rather than alphabetically — the first is the one to
    # take if you do not care.
    offers = (STANDARD_ARRAY, ROLL_4D6, POINT_BUY)
    hit_dice = {
        "barbarian": 12,
        "fighter": 10, "paladin": 10, "ranger": 10,
        "bard": 8, "cleric": 8, "druid": 8, "monk": 8, "rogue": 8, "warlock": 8,
        "sorcerer": 6, "wizard": 6,
    }
    modules = (
        Module(
            slug="the-drowned-belfry",
            title="The Drowned Belfry",
            premise=(
                "A bell tower stands sunk to its eaves in the marsh outside "
                "Ashfen, and on cold nights it still rings. The village has "
                "stopped asking why. Something below the waterline is keeping "
                "time, and it is counting down to something."
            ),
            hook=(
                "Ashfen's reeve has scraped together sixty marks to have "
                "the ringing stopped, and has stopped pretending it is "
                "about the noise. Three people have gone out along the "
                "causeway this month. The tolls are coming closer "
                "together, and the reeve wants you gone before dark "
                "tomorrow, one way or the other."
            ),
            opening="the causeway into Ashfen marsh, at dusk",
        ),
        Module(
            slug="the-ashfen-road",
            title="The Ashfen Road",
            premise=(
                "Three carters have gone missing on a stretch of road with "
                "nowhere to hide. The ruts stop mid-track. The horses came "
                "back, calm and well fed, and will not be led that way again."
            ),
            hook=(
                "The carters' guild will pay for its three drivers found, "
                "alive or otherwise, and will pay more if you can say why "
                "the horses were not. The next convoy leaves at first "
                "light and nobody has told those drivers anything."
            ),
            opening="the last waystation before the missing stretch of road",
        ),
    )
