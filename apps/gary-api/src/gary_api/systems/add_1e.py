from gary_api.systems.base import Module, TwoDegrees


class ADnD1e(TwoDegrees):
    slug = "add-1e"
    name = "Advanced Dungeons & Dragons 1st Edition"
    blurb = (
        "Deadly, procedural and unsentimental. Descending armour class, saving "
        "throws by category, and characters who die at 0 hit points. Reward "
        "caution and clever play over combat; a party that avoids a fight has "
        "played well, not skipped content."
    )
    classes = (
        "assassin", "bard", "cleric", "druid", "fighter", "illusionist",
        "magic-user", "monk", "paladin", "ranger", "thief",
    )
    modules = (
        Module(
            slug="the-moaning-barrow",
            title="The Moaning Barrow",
            premise=(
                "A long barrow on the heath that sounds, in certain winds, "
                "like a man trying to be heard through a wall. It has been "
                "opened twice in living memory. Both parties came out. Neither "
                "came out with everyone."
            ),
            opening="the heath above the barrow, in a rising wind",
        ),
        Module(
            slug="the-seven-doors-of-vashk",
            title="The Seven Doors of Vashk",
            premise=(
                "A sorcerer's tomb with seven doors and one key, which fits "
                "all of them and can only be turned six times. Vashk built it "
                "that way on purpose and left a note saying so."
            ),
            opening="the antechamber, the key cold in your hand",
        ),
    )
