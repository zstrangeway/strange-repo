from gary_api.dice import Roll
from gary_api.systems.base import (
    ROLL_3D6_IN_ORDER,
    ROLL_4D6,
    Module,
    SystemError,
    TwoDegrees,
)


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
    # Three dice straight down the page is the Player's Handbook, and four
    # dropping the lowest and arranged is the Dungeon Master's Guide's own
    # Method I. Both are first edition; neither is a point buy, which is not.
    offers = (ROLL_3D6_IN_ORDER, ROLL_4D6)
    hit_dice = {
        "fighter": 10, "paladin": 10,
        "cleric": 8, "druid": 8, "ranger": 8,
        "assassin": 6, "bard": 6, "thief": 6,
        "illusionist": 4, "magic-user": 4, "monk": 4,
    }
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
            hook=(
                "The heath's tenants have petitioned to have the barrow "
                "sealed for good, and the reeve will not seal it until "
                "somebody goes down and says what is in it. There is coin "
                "in the answer and more in whatever the last two parties "
                "left behind them."
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
            hook=(
                "You bought the key, and the seller was glad to be rid of "
                "it. Six turns is what you have, seven doors is what Vashk "
                "built, and whatever is worth having is behind one of "
                "them. Nobody is coming to let you out."
            ),
            opening="the antechamber, the key cold in your hand",
        ),
    )

    def modifier(self, score: int) -> int:
        """Nothing, and deliberately.

        First edition has no single ability modifier to apply. It has a
        different table per ability — strength gives hit and damage
        adjustments off its own row, dexterity gives reaction and missile
        adjustments off another — and no general ability check to spend one
        on. Returning `(score - 10) // 2` here would be quietly running third
        edition's rule in a first edition game, which is the drift the engines
        exist to stop. Zero until somebody types the real tables in.
        """
        return 0

    def initiative(self, modifier: int) -> Roll:
        """Not yet, and refused rather than approximated.

        First edition rolls one d6 per *side* and moves whole sides at a
        time. That is a different shape from the flat, per-combatant order
        everything downstream of this assumes — not a different number in the
        same shape — so rolling a die each and sorting them would write a log
        recording something that never happened at a first edition table.
        """
        raise SystemError(
            "first edition rolls initiative by side, which is not built yet"
        )
