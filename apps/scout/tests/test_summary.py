"""The change summary — the half of the safety story a check cannot cover."""

import unittest

from scout import summary


class Sections(unittest.TestCase):
    def test_a_preamble_above_the_first_heading_counts(self):
        found = summary.sections("Ada Lovelace\n\n## Skills\n\nPython\n")
        self.assertEqual([s.heading for s in found], ["", "Skills"])

    def test_an_empty_preamble_does_not(self):
        found = summary.sections("\n\n## Skills\n\nPython\n")
        self.assertEqual([s.heading for s in found], ["Skills"])


class Rendering(unittest.TestCase):
    def test_an_unchanged_draft_still_says_something(self):
        rendered = summary.compute("## A\n\nx\n", "## A\n\nx\n").render()
        self.assertIn("nothing changed", rendered)

    def test_a_dropped_section_is_named(self):
        rendered = summary.compute("## A\n\nx\n\n## B\n\ny\n", "## A\n\nx\n").render()
        self.assertIn("left out      B", rendered)

    def test_a_new_section_is_named(self):
        rendered = summary.compute("## A\n\nx\n", "## A\n\nx\n\n## B\n\ny\n").render()
        self.assertIn("new section   B", rendered)

    def test_a_rewritten_line_is_shown_before_and_after(self):
        rendered = summary.compute(
            "- led a team of 3\n", "- led a team of 12\n"
        ).render()
        self.assertIn("rewritten     - led a team of 3", rendered)
        self.assertIn("-> - led a team of 12", rendered)


class Rewrites(unittest.TestCase):
    def test_the_list_stops_rather_than_printing_a_whole_resume(self):
        master = "\n".join(f"- line {n}" for n in range(20))
        draft = "\n".join(f"- changed {n}" for n in range(20))
        self.assertEqual(len(summary.compute(master, draft, rewrites=3).rewritten), 3)

    def test_dropping_a_section_does_not_report_the_rest_as_moved(self):
        master = "## A\n\nx\n\n## B\n\ny\n\n## C\n\nz\n"
        draft = "## A\n\nx\n\n## C\n\nz\n"
        computed = summary.compute(master, draft)
        self.assertEqual(computed.moved_up, [])
        self.assertEqual(computed.moved_down, [])
        self.assertEqual(computed.dropped, ["B"])
