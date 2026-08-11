"""The dice, and the notation gary will and will not roll.

Every refusal here is one a model can cause by asking for something that
reads like dice and is not. They reach the player as a refusal rather than a
traceback, so they are worth pinning.
"""

import unittest
from unittest.mock import patch

from gary_api import dice


class NotationTests(unittest.TestCase):
    def test_plain(self):
        made = dice.roll("1d20")
        self.assertEqual(len(made.dice), 1)
        self.assertTrue(1 <= made.total <= 20)
        self.assertEqual(made.modifier, 0)

    def test_with_a_bonus(self):
        made = dice.roll("2d6+3", "Damage")
        self.assertEqual(len(made.dice), 2)
        self.assertEqual(made.modifier, 3)
        self.assertEqual(made.total, sum(made.dice) + 3)
        self.assertEqual(made.reason, "Damage")

    def test_with_a_penalty(self):
        made = dice.roll("1d20-2")
        self.assertEqual(made.modifier, -2)
        self.assertEqual(made.total, made.dice[0] - 2)

    def test_tolerates_spacing_and_case(self):
        self.assertEqual(dice.roll(" 1 D 20 + 1 ").modifier, 1)

    def test_refuses_what_is_not_dice(self):
        for notation in ("1d20+lots", "", "d20", "two d six", "1d20+", None, "20"):
            with self.subTest(notation=notation), self.assertRaises(dice.DiceError):
                dice.roll(notation)

    def test_refuses_a_handful_that_is_not_a_handful(self):
        with self.assertRaises(dice.DiceError):
            dice.roll("0d6")
        with self.assertRaises(dice.DiceError):
            dice.roll(f"{dice.MAX_DICE + 1}d6")

    def test_refuses_a_die_that_does_not_exist(self):
        with self.assertRaises(dice.DiceError):
            dice.roll("1d1")
        with self.assertRaises(dice.DiceError):
            dice.roll(f"1d{dice.MAX_SIDES + 1}")

    def test_keeps_the_dice_and_not_just_the_total(self):
        # "17" and "a 14 and a 3" are different things to read, and a natural
        # 20 is worth knowing about.
        made = dice.roll("3d6")
        self.assertEqual(made.total, sum(made.dice))
        self.assertEqual(len(made.dice), 3)


class SeedingTests(unittest.TestCase):
    def tearDown(self):
        dice.reseed()

    def test_the_same_seed_rolls_the_same_dice(self):
        dice.seed(7)
        first = [dice.roll("1d20").total for _ in range(5)]
        dice.seed(7)
        self.assertEqual(first, [dice.roll("1d20").total for _ in range(5)])

    def test_different_seeds_generally_differ(self):
        dice.seed(1)
        first = [dice.roll("1d100").total for _ in range(10)]
        dice.seed(2)
        self.assertNotEqual(first, [dice.roll("1d100").total for _ in range(10)])

    def test_configure_reads_the_environment(self):
        with patch.dict("os.environ", {"DICE_SEED": "11"}):
            dice.configure()
            first = dice.roll("1d20").total
        with patch.dict("os.environ", {"DICE_SEED": "11"}):
            dice.configure()
            self.assertEqual(first, dice.roll("1d20").total)

    def test_configure_without_a_seed_still_rolls(self):
        with patch.dict("os.environ", {}, clear=True):
            dice.configure()
            self.assertTrue(1 <= dice.roll("1d20").total <= 20)


if __name__ == "__main__":
    unittest.main()


class ModifierTests(unittest.TestCase):
    def test_reads_what_a_notation_adds(self):
        self.assertEqual(dice.modifier_in("1d20+3"), 3)
        self.assertEqual(dice.modifier_in("1d20-1"), -1)
        self.assertEqual(dice.modifier_in("1d20"), 0)

    def test_refuses_what_it_cannot_read(self):
        # Asked before a roll for somebody is allowed through, so nonsense has
        # to fail here rather than at the roll.
        with self.assertRaises(dice.DiceError):
            dice.modifier_in("1d20+lots")
