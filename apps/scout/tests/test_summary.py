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


class DeletionsAreNotRewrites(unittest.TestCase):
    """The defect the first real smoke run found.

    Position-aligned diffing paired a bullet the model deleted with an
    unrelated one it promoted, and reported the pair as a rewrite. The summary
    is the only thing that catches inflation, so a summary that invents an
    edit is worse than one that says less.
    """

    MASTER = (
        "- Cut deploy time from 40 minutes to 4\n"
        "- Led a team of 3 through the billing migration, with no downtime\n"
        "- Ran the Postgres upgrade across 40 services\n"
    )

    def test_a_cut_bullet_and_a_promoted_one_are_not_a_rewrite(self):
        draft = (
            "- Ran the Postgres upgrade across 40 services\n"
            "- Led a team of 3 through the billing migration, with no downtime\n"
        )
        computed = summary.compute(self.MASTER, draft)
        self.assertEqual(computed.rewritten, [])
        self.assertEqual(computed.cut, ["- Cut deploy time from 40 minutes to 4"])

    def test_a_line_that_only_moved_is_not_reported_as_cut(self):
        draft = (
            "- Ran the Postgres upgrade across 40 services\n"
            "- Cut deploy time from 40 minutes to 4\n"
            "- Led a team of 3 through the billing migration, with no downtime\n"
        )
        computed = summary.compute(self.MASTER, draft)
        self.assertEqual(computed.cut, [])
        self.assertEqual(computed.rewritten, [])

    def test_a_genuine_reword_is_still_paired(self):
        draft = self.MASTER.replace("a team of 3", "a team of 12")
        computed = summary.compute(self.MASTER, draft)
        self.assertEqual(len(computed.rewritten), 1)
        before, after = computed.rewritten[0]
        self.assertIn("team of 3", before)
        self.assertIn("team of 12", after)
        self.assertEqual(computed.cut, [])

    def test_a_new_line_is_named_as_new(self):
        draft = self.MASTER + "- Wrote the Terraform for every environment\n"
        computed = summary.compute(self.MASTER, draft)
        self.assertEqual(
            computed.fresh, ["- Wrote the Terraform for every environment"]
        )

    def test_a_heading_is_not_reported_as_a_cut_line(self):
        # It is reported as its section moving or being left out; twice is
        # noise that buries the bullets.
        computed = summary.compute("## Skills\n\nPython\n", "## Skills\n\nPython\n")
        self.assertEqual(computed.cut, [])
        self.assertEqual(computed.fresh, [])

    def test_the_render_names_cuts_and_new_lines(self):
        draft = "- Ran the Postgres upgrade across 40 services\n"
        rendered = summary.compute(self.MASTER, draft).render()
        self.assertIn("cut           - Cut deploy time", rendered)


class Comments(unittest.TestCase):
    """`scout init` writes the format rules into master.md as an HTML comment.

    A model quite reasonably drops it. Before this, the first real smoke run
    reported seven lines of scout's own instructions as content the draft had
    cut — noise on top of the two changes that mattered.
    """

    MASTER = (
        "<!--\nscout reads this file's structure.\nTwo rules matter.\n-->\n\n"
        "## Skills\n\nPython\n"
    )

    def test_a_dropped_comment_is_not_reported_as_cut_content(self):
        computed = summary.compute(self.MASTER, "## Skills\n\nPython\n")
        self.assertEqual(computed.cut, [])
        self.assertEqual(computed.rewritten, [])

    def test_a_kept_comment_is_not_reported_either(self):
        computed = summary.compute(self.MASTER, self.MASTER)
        self.assertEqual(computed.cut, [])
        self.assertEqual(computed.fresh, [])

    def test_a_comment_on_one_line_closes_itself(self):
        master = "<!-- a note -->\n\n## Skills\n\nPython\n"
        self.assertEqual(summary.compute(master, "## Skills\n\nPython\n").cut, [])
