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


class Dates(unittest.TestCase):
    """Added after the first real smoke run handed one employer another's dates."""

    MASTER = """# Ada

## Skills

Python

## Experience

### Wilding Labs — Senior Engineer

2021–2025

- Ran the Postgres upgrade

### Thornfield Systems — Platform Engineer

2018–2021

- Built the Python services
"""

    def test_an_employer_given_another_employer_s_dates(self):
        # Every year here appears in the master. What is wrong is which
        # employer they sit under, which is why this is checked per section
        # rather than over the document.
        draft = self.MASTER.replace(
            "### Thornfield Systems — Platform Engineer\n\n2018–2021",
            "### Thornfield Systems — Platform Engineer\n\n2021–2025",
        )
        findings = grounding.check(self.MASTER, draft)
        self.assertEqual([f.kind for f in findings], ["date"])
        self.assertEqual(
            str(findings[0]),
            '"2025" is not a date the master resume gives for "Thornfield Systems"',
        )

    def test_the_same_dates_written_with_a_different_dash(self):
        draft = self.MASTER.replace("2021–2025", "2021 - 2025")
        self.assertEqual(grounding.check(self.MASTER, draft), [])

    def test_dropping_the_dates_is_allowed(self):
        # Cutting is within what tailoring may do; only adding is not.
        draft = self.MASTER.replace("\n2018–2021\n", "\n")
        self.assertEqual(grounding.check(self.MASTER, draft), [])

    def test_a_year_nobody_ever_worked(self):
        draft = self.MASTER.replace("2021–2025", "2021–2026")
        self.assertEqual(
            [f.term for f in grounding.check(self.MASTER, draft)], ["2026"]
        )

    def test_an_invented_employer_is_not_also_reported_for_its_dates(self):
        # The employer is the finding. Adding "and its dates are wrong too" is
        # noise on top of a refusal that already says enough.
        draft = self.MASTER + "\n### Initech — Senior Engineer\n\n2019–2020\n"
        kinds = [f.kind for f in grounding.check(self.MASTER, draft)]
        self.assertEqual(kinds, ["employer"])

    def test_years_outside_any_employer_are_not_attributed_to_one(self):
        # A `## Education` section closes the employer above it, so its dates
        # are not checked against that employer's.
        draft = self.MASTER + "\n## Education\n\n2014–2017\n"
        self.assertEqual(grounding.check(self.MASTER, draft), [])


class Scanning(unittest.TestCase):
    """The advisory sibling of `check`, for text that is not a projection."""

    POSTING = "We want deep Kubernetes experience and strong Postgres skills."

    def test_it_refuses_nothing_and_returns_what_it_noticed(self):
        found = grounding.scan(MASTER, "I am an expert in Kubernetes.", self.POSTING)
        self.assertEqual([f.term for f in found], ["Kubernetes"])

    def test_a_name_the_posting_asks_for_is_marked_as_such(self):
        # The riskiest shape: in the advert, not in the resume, which is what
        # somebody writes because they were asked for it.
        found = grounding.scan(MASTER, "I am an expert in Kubernetes.", self.POSTING)
        self.assertTrue(found[0].from_posting)

    def test_a_name_in_neither_is_not(self):
        found = grounding.scan(MASTER, "I once wrote Fortran.", self.POSTING)
        self.assertEqual([f.term for f in found], ["Fortran"])
        self.assertFalse(found[0].from_posting)

    def test_what_the_posting_asks_for_comes_first(self):
        found = grounding.scan(
            MASTER, "I know Fortran and Kubernetes well.", self.POSTING
        )
        self.assertEqual([f.term for f in found], ["Kubernetes", "Fortran"])

    def test_words_from_the_master_are_not_flagged(self):
        self.assertEqual(grounding.scan(MASTER, "I ran the Postgres upgrade."), [])

    def test_it_works_with_no_posting_to_compare_against(self):
        found = grounding.scan(MASTER, "I am an expert in Kubernetes.")
        self.assertFalse(found[0].from_posting)


class RealResumeShapes(unittest.TestCase):
    """Shapes found in an actual resume rather than in a fixture.

    Every one of these was silently wrong until a real four-page resume was
    pointed at the parser. The skills one is the worst kind of bug this
    project can have: the check reported nothing to catch because it had
    found nothing to check against.
    """

    def test_a_section_called_technical_skills(self):
        markdown = "## Technical Skills\n\nTypeScript, Python\n\n## Experience\n"
        self.assertEqual(
            grounding.Master.parse(markdown).skills, frozenset({"typescript", "python"})
        )

    def test_a_section_called_core_competencies(self):
        markdown = "## Core Competencies\n\nCloud Architecture, CI/CD Automation\n"
        self.assertIn("ci/cd automation", grounding.Master.parse(markdown).skills)

    def test_skills_grouped_under_their_own_labels(self):
        # "Languages: TypeScript, Python" is one line naming two skills, not
        # one skill called "Languages: TypeScript".
        markdown = (
            "## Technical Skills\n\n"
            "Languages: TypeScript, Python\n"
            "Frontend: React, Vue.js\n"
        )
        skills = grounding.Master.parse(markdown).skills
        self.assertIn("typescript", skills)
        self.assertIn("react", skills)
        self.assertNotIn("languages: typescript", skills)

    def test_a_parenthesised_group_of_skills(self):
        markdown = "## Skills\n\nAWS (Lambda, S3, CDK), Docker\n"
        skills = grounding.Master.parse(markdown).skills
        self.assertIn("docker", skills)
        self.assertIn("s3", skills)

    def test_an_employer_with_an_abbreviation_after_it(self):
        markdown = "### Amazon Web Services (AWS) – Software Engineer\n"
        master = grounding.Master.parse(markdown)
        self.assertIn("amazon web services aws", master.employers)

    def test_a_draft_may_name_a_skill_the_master_groups_under_a_label(self):
        markdown = (
            "## Technical Skills\n\nLanguages: TypeScript, Python\n\n"
            "## Experience\n\n### Arine – Senior Software Engineer\n"
        )
        draft = (
            "## Technical Skills\n\nTypeScript\n\n"
            "### Arine – Senior Software Engineer\n"
        )
        self.assertEqual(grounding.check(markdown, draft), [])


class PluralsAndPossessives(unittest.TestCase):
    """Found by the first paid run, on a real resume.

    A model wrote "from backend APIs to frontend UIs". The master says "UI
    testing workflows", so "UIs" was not in it and a completely honest resume
    was refused. A false refusal is worse for somebody than a missed
    invention: it is the failure that teaches people to stop reading refusals.
    """

    MASTER = """# Ada

## Skills

UI, API, Postgres

## Experience

### Wilding Labs — Senior Engineer

- Optimized UI testing workflows and the API behind them
"""

    def test_a_plural_of_something_in_the_master(self):
        self.assertEqual(grounding.check(self.MASTER, "- Built the UIs\n"), [])

    def test_a_plural_at_the_end_of_a_sentence(self):
        # "…from backend APIs to frontend UIs." — the full stop is not part
        # of the word, and missing that is what made the first fix not work.
        self.assertEqual(grounding.check(self.MASTER, "- Built the UIs.\n"), [])

    def test_an_es_plural(self):
        master = "## Skills\n\nIndex\n"
        self.assertEqual(grounding.check(master, "- Rebuilt the Indexes\n"), [])

    def test_a_singular_of_something_the_master_pluralises(self):
        master = "## Skills\n\nAPIs\n"
        self.assertEqual(grounding.check(master, "- Wrote the API\n"), [])

    def test_a_possessive(self):
        self.assertEqual(grounding.check(self.MASTER, "- Ran Postgres's upgrade\n"), [])

    def test_a_compound_of_two_things_in_the_master(self):
        # "10+ years across TypeScript/React and Python" — a model joining two
        # things somebody actually has is not claiming a third thing.
        master = "## Skills\n\nTypeScript, React, Postgres\n"
        self.assertEqual(
            grounding.check(master, "- Built it in TypeScript/React\n"), []
        )

    def test_a_hyphenated_compound(self):
        master = "## Skills\n\nPostgres, Python\n"
        self.assertEqual(grounding.check(master, "- Wrote Python-Postgres glue\n"), [])

    def test_a_compound_hiding_something_new_is_still_caught(self):
        # The relaxation must not become a way through: one half being real
        # does not make the other half real.
        master = "## Skills\n\nTypeScript\n"
        found = grounding.check(master, "- Built it in TypeScript/Kubernetes\n")
        self.assertEqual([f.term for f in found], ["TypeScript/Kubernetes"])

    def test_a_plural_of_something_that_is_not_there_is_still_caught(self):
        # The relaxation must not become a way through. "Kubernetes" is not a
        # plural of anything in the master.
        found = grounding.check(self.MASTER, "- Ran the Kubernetes clusters\n")
        self.assertEqual([f.term for f in found], ["Kubernetes"])

    def test_a_short_word_is_not_stripped_into_a_match(self):
        # "AWS" must not become "AW" and match something by accident.
        master = "## Skills\n\nAW\n"
        self.assertEqual(
            [f.term for f in grounding.check(master, "- Used AWS\n")], ["AWS"]
        )
