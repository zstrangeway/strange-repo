from gary_api.systems.base import Module, TwoDegrees


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
            opening="the last waystation before the missing stretch of road",
        ),
    )
