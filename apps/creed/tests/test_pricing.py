"""The cost table's shapes, including ones the fixture does not contain."""

import unittest

from creed import pricing


def rows(*entries):
    return [
        {"line": str(index), "description": description, "cost": cost}
        for index, (description, cost) in enumerate(entries, start=1)
    ]


class TestTierShapes(unittest.TestCase):
    def test_flat_price(self):
        parsed = pricing.parse(rows(("YOUR UNIT COSTS", ""), ("1 model", "100")))
        self.assertFalse(parsed.escalates)
        self.assertEqual(parsed.cost_for(1), 100)
        self.assertEqual(parsed.tiers[0].label, "any")

    def test_first_only_then_open_ended(self):
        parsed = pricing.parse(
            rows(
                ("YOUR 1ST UNIT COSTS", ""),
                ("1 model", "100"),
                ("YOUR 2ND + UNIT COSTS", ""),
                ("1 model", "120"),
            )
        )
        self.assertEqual([tier.label for tier in parsed.tiers], ["1", "2+"])
        self.assertEqual(parsed.cost_for(1, 1), 100)
        self.assertEqual(parsed.cost_for(1, 2), 120)
        self.assertEqual(parsed.cost_for(1, 9), 120)

    def test_a_range_then_open_ended(self):
        parsed = pricing.parse(
            rows(
                ("YOUR 1ST TO 3RD UNITS COST", ""),
                ("5 models", "100"),
                ("YOUR 4TH + UNIT COSTS", ""),
                ("5 models", "130"),
            )
        )
        self.assertEqual([tier.label for tier in parsed.tiers], ["1-3", "4+"])
        self.assertEqual(parsed.cost_for(5, 3), 100)
        self.assertEqual(parsed.cost_for(5, 4), 130)

    def test_a_size_the_datasheet_does_not_come_in(self):
        parsed = pricing.parse(rows(("YOUR UNIT COSTS", ""), ("5 models", "100")))
        # None rather than a guess: an invented number would be
        # indistinguishable from a real one everywhere downstream.
        self.assertIsNone(parsed.cost_for(7))

    def test_no_rows_at_all(self):
        parsed = pricing.parse([])
        self.assertEqual(parsed.tiers, [])
        self.assertEqual(parsed.sizes, [])
        self.assertIsNone(parsed.cost_for(5))
        self.assertIsNone(parsed.tier_for(1))

    def test_value_row_with_no_header_above_it(self):
        parsed = pricing.parse(rows(("1 model", "90")))
        self.assertEqual(parsed.cost_for(1), 90)

    def test_ordinal_past_every_tier_uses_the_last(self):
        parsed = pricing.parse(
            rows(
                ("YOUR 1ST UNIT COSTS", ""),
                ("1 model", "100"),
            )
        )
        self.assertEqual(parsed.tier_for(5).label, "1")


class TestWargearAndVariants(unittest.TestCase):
    def test_priced_wargear_is_kept_apart(self):
        parsed = pricing.parse(
            rows(
                ("YOUR UNIT COSTS", ""),
                ("1 model", "100"),
                ("WARGEAR OPTIONS", ""),
                ("per Multi-melta", "10"),
            )
        )
        self.assertEqual(parsed.cost_for(1), 100)
        self.assertEqual(parsed.wargear_cost("per Multi-melta"), 10)
        self.assertEqual(parsed.wargear_cost("PER MULTI-MELTA"), 10)
        self.assertIsNone(parsed.wargear_cost("per Nothing"))
        self.assertTrue(parsed.wargear[0].is_per_item)

    def test_variants_of_the_whole_datasheet(self):
        parsed = pricing.parse(
            rows(
                ('<div class="dsHeaderAoI">AGENTS Detachment</div>', ""),
                ("YOUR UNIT COSTS", ""),
                ("1 model", "110"),
                ('<div class="dsHeaderAoI">Assigned Agent</div>', ""),
                ("YOUR UNIT COSTS", ""),
                ("1 model", "125"),
            )
        )
        self.assertEqual(len(parsed.variants), 2)
        self.assertEqual(parsed.variants[0].name, "AGENTS Detachment")
        self.assertEqual(parsed.variants[1].name, "Assigned Agent")
        # "The" price is the first variant's.
        self.assertEqual(parsed.cost_for(1), 110)


class TestOddRows(unittest.TestCase):
    def test_a_note_is_kept_not_dropped(self):
        parsed = pricing.parse(
            rows(
                ("YOUR UNIT COSTS", ""),
                ("1 model", "100"),
                ("WARGEAR COSTS REMOVED", ""),
            )
        )
        self.assertIn("WARGEAR COSTS REMOVED", parsed.notes)

    def test_an_unrecognised_header_is_kept(self):
        parsed = pricing.parse(rows(("SOMETHING NEW UPSTREAM", ""), ("1 model", "50")))
        self.assertIn("SOMETHING NEW UPSTREAM", parsed.notes)
        self.assertEqual(parsed.cost_for(1), 50)

    def test_a_cost_that_is_not_a_number(self):
        parsed = pricing.parse(rows(("YOUR UNIT COSTS", ""), ("1 model", "free")))
        self.assertIn("1 model: free", parsed.notes)
        self.assertIsNone(parsed.cost_for(1))

    def test_html_comments_and_blank_rows_are_ignored(self):
        parsed = pricing.parse(
            rows(("", ""), ("YOUR UNIT COSTS", ""), ("+ <!-- -->1 Invader ATV", "35"))
        )
        self.assertEqual(parsed.tiers[0].options[0].description, "+ 1 Invader ATV")
        self.assertEqual(parsed.tiers[0].options[0].models, None)

    def test_a_named_composition_rather_than_a_model_count(self):
        parsed = pricing.parse(
            rows(("YOUR UNIT COSTS", ""), ("3 Wolf Guard Headtakers", "75"))
        )
        self.assertEqual(parsed.sizes, [3])
        self.assertEqual(parsed.cost_for(3), 75)
