"""The check, at the edges the specs cannot reach through the CLI."""

import unittest

from scout import grounding

MASTER = """# Ada

## Skills

Python, Postgres

## Experience

### Wilding Labs — Senior Engineer

- Ran the Postgres upgrade
"""


class Normalising(unittest.TestCase):
    def test_strips_punctuation_from_both_ends(self):
        self.assertEqual(grounding.normalise("*Postgres.*"), "postgres")

    def test_keeps_the_characters_that_are_part_of_a_name(self):
        self.assertEqual(grounding.normalise("C++,"), "c++")


class Parsing(unittest.TestCase):
    def test_a_heading_without_a_job_title(self):
        self.assertEqual(
            grounding.headings("### Wilding Labs"), [("Wilding Labs", None)]
        )

    def test_skills_split_on_bullets_as_well_as_commas(self):
        markdown = "## Skills\n\n- Python\n- Postgres\n\n## Experience\n\n- ignored\n"
        self.assertEqual(grounding.skills(markdown), ["Python", "Postgres"])

    def test_an_employer_with_no_job_title_beside_it(self):
        # Plenty of resumes write the company alone and the title on the next
        # line. That heading still names an employer.
        master = grounding.Master.parse("### Wilding Labs\n### Thornfield — Engineer\n")
        self.assertEqual(master.employers, frozenset({"wilding labs", "thornfield"}))
        self.assertEqual(master.titles, frozenset({"engineer"}))

    def test_a_master_with_no_skills_section(self):
        self.assertEqual(grounding.Master.parse("# Ada\n").skills, frozenset())


class Checking(unittest.TestCase):
    def test_an_invented_job_title_is_caught(self):
        findings = grounding.check(MASTER, "### Wilding Labs — Chief Executive\n")
        self.assertEqual(
            [(f.kind, f.term) for f in findings], [("title", "Chief Executive")]
        )

    def test_a_technology_in_lower_case_is_caught(self):
        # The capitalisation sweep would walk straight past this one, which is
        # the entire reason KNOWN_TECHNOLOGIES exists.
        findings = grounding.check(MASTER, "- Ran it all on kubernetes\n")
        self.assertEqual([f.term for f in findings], ["kubernetes"])

    def test_a_word_that_only_starts_a_sentence_is_not_a_claim(self):
        self.assertEqual(grounding.check(MASTER, "- Ran the Postgres upgrade\n"), [])

    def test_a_date_is_not_a_claim(self):
        self.assertEqual(grounding.check(MASTER, "- Ran it 2021 to 2025\n"), [])

    def test_a_month_is_not_a_claim(self):
        self.assertEqual(grounding.check(MASTER, "- Shipped it in March\n"), [])

    def test_the_same_invention_twice_is_reported_once(self):
        draft = "- Used Kubernetes here\n- And Kubernetes there\n"
        self.assertEqual(
            [f.term for f in grounding.check(MASTER, draft)], ["Kubernetes"]
        )

    def test_a_finding_says_what_it_is(self):
        finding = grounding.Finding("skill", "Kubernetes")
        self.assertEqual(str(finding), '"Kubernetes" is not in the master resume')
