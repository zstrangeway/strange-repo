"""The package, at the seams the CLI would contort to reach."""

from mcp.server.mcpserver.exceptions import ToolError
from support import InAScratchHome

from scout import db, mcp_server, packages, postings, tailoring
from scout.errors import ScoutError
from scout.providers.fake import FakeProvider

MASTER = """# Ada

## Skills

Python, Postgres

## Experience

### Wilding Labs — Senior Engineer

2021–2025

- Ran the Postgres upgrade
- Built the Python services
"""


class Packages(InAScratchHome):
    def setUp(self):
        super().setUp()
        (self.home / "resumes").mkdir(parents=True, exist_ok=True)
        (self.home / "resumes" / "master.md").write_text(MASTER, encoding="utf-8")
        self.ref = self.save()

    def _tailor(self, draft=None):
        directory = self.home / ".scout"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "fake-draft.md").write_text(draft or MASTER, encoding="utf-8")
        with db.connect() as connection:
            tailoring.tailor(connection, self.ref, FakeProvider())

    def test_reading_a_package_that_was_never_assembled(self):
        # Distinct from a posting that does not exist: the posting is fine,
        # nobody has started a package for it.
        self._tailor()
        with db.connect() as connection, self.assertRaises(ScoutError) as caught:
            packages.read(connection, self.ref)
        self.assertIn("no package for", str(caught.exception))

    def test_a_package_before_anything_was_approved_has_nothing_to_compare(self):
        self._tailor()
        with db.connect() as connection:
            package = packages.assemble(connection, self.ref)
        self.assertEqual(package.changed_since_approval, [])
        self.assertFalse(package.approved)

    def test_an_answer_that_disappears_is_a_change(self):
        # Approval is of a set of words. Removing one of them is as much a
        # change as rewriting it, and would otherwise leave the approval
        # standing over a package that no longer says what was approved.
        self._tailor()
        with db.connect() as connection:
            packages.add_answer(connection, self.ref, "Why us?", "Because.")
            approved = packages.approve(connection, self.ref)
            self.assertTrue(approved.approved)
            connection.execute("DELETE FROM answers")
            package = packages.read(connection, self.ref)
        self.assertFalse(package.approved)
        self.assertIn("Why us?", package.changed_since_approval)

    def test_re_assembling_does_not_start_a_second_package(self):
        self._tailor()
        with db.connect() as connection:
            packages.add_answer(connection, self.ref, "Why us?", "Because.")
            packages.assemble(connection, self.ref)
            package = packages.read(connection, self.ref)
            rows = connection.execute("SELECT COUNT(*) AS n FROM packages").fetchone()
        self.assertEqual(rows["n"], 1)
        self.assertEqual(len(package.items), 2)

    def test_an_answer_replaces_an_earlier_one_to_the_same_question(self):
        # Two answers to one question would both be submitted, and a session
        # correcting itself is the ordinary way that happens.
        self._tailor()
        with db.connect() as connection:
            packages.add_answer(connection, self.ref, "Why us?", "First try.")
            packages.add_answer(connection, self.ref, "Why us?", "Better answer.")
            package = packages.read(connection, self.ref)
        answers = [item for item in package.items if item.kind == "answer"]
        self.assertEqual(len(answers), 1)
        self.assertEqual(answers[0].body, "Better answer.")

    def test_the_resume_comes_off_disk_rather_than_out_of_the_row(self):
        # What would actually be attached is the file. If somebody edited it
        # by hand, that is what they are approving.
        self._tailor()
        with db.connect() as connection:
            package = packages.assemble(connection, self.ref)
            path = self.home / "resumes" / self.ref / "v1.md"
            path.write_text(MASTER + "\n- Edited by hand\n", encoding="utf-8")
            package = packages.read(connection, self.ref)
        self.assertIn("Edited by hand", package.items[0].body)

    def test_an_empty_answer_is_refused(self):
        self._tailor()
        with db.connect() as connection, self.assertRaises(ScoutError) as caught:
            packages.add_answer(connection, self.ref, "Why us?", "   ")
        self.assertIn("empty", str(caught.exception))

    def test_a_package_for_a_posting_that_does_not_exist(self):
        with db.connect() as connection, self.assertRaises(ScoutError) as caught:
            packages.assemble(connection, "no-such-posting")
        self.assertIn("no posting called", str(caught.exception))

    def test_a_posting_with_no_tailored_resume(self):
        with db.connect() as connection, self.assertRaises(ScoutError) as caught:
            packages.assemble(connection, self.ref)
        self.assertIn("no tailored resume", str(caught.exception))


class Rendering(InAScratchHome):
    def setUp(self):
        super().setUp()
        (self.home / "resumes").mkdir(parents=True, exist_ok=True)
        (self.home / "resumes" / "master.md").write_text(MASTER, encoding="utf-8")
        self.ref = self.save()
        with db.connect() as connection:
            tailoring.tailor(connection, self.ref, FakeProvider())

    def test_a_package_of_only_checked_things_says_so(self):
        with db.connect() as connection:
            rendered = packages.assemble(connection, self.ref).render()
        self.assertIn("Everything in this package was checked", rendered)
        self.assertNotIn("NOT everything", rendered)

    def test_one_unchecked_answer_changes_what_it_claims(self):
        with db.connect() as connection:
            packages.add_answer(connection, self.ref, "Why us?", "Because.")
            rendered = packages.read(connection, self.ref).render()
        self.assertIn("NOT everything in this package was checked", rendered)
        self.assertIn(packages.SCANNED_MEANS, rendered)

    def test_a_withdrawn_approval_says_what_moved(self):
        with db.connect() as connection:
            packages.add_answer(connection, self.ref, "Why us?", "Because.")
            packages.approve(connection, self.ref)
            packages.add_answer(connection, self.ref, "Why us?", "Something else.")
            rendered = packages.read(connection, self.ref).render()
        self.assertIn("NOT approved", rendered)
        self.assertIn("Why us?", rendered)
        self.assertIn("approved again", rendered)

    def test_a_package_nobody_has_looked_at_yet(self):
        with db.connect() as connection:
            rendered = packages.assemble(connection, self.ref).render()
        self.assertIn("Not approved yet", rendered)


class ThroughTheServer(InAScratchHome):
    """The tool wrappers' refusal paths, which the Gherkin covers only happily."""

    def test_the_package_tool_refuses_a_posting_that_is_not_there(self):

        with self.assertRaises(ToolError) as caught:
            mcp_server.get_package("no-such-posting")
        self.assertIn("no posting called", str(caught.exception))

    def test_the_answer_tool_refuses_an_empty_answer(self):

        (self.home / "resumes").mkdir(parents=True, exist_ok=True)
        (self.home / "resumes" / "master.md").write_text(MASTER, encoding="utf-8")
        ref = self.save()
        with db.connect() as connection:
            tailoring.tailor(connection, ref, FakeProvider())
        with self.assertRaises(ToolError) as caught:
            mcp_server.add_answer(ref, "Why us?", "  ")
        self.assertIn("empty", str(caught.exception))

    def test_the_approve_tool_refuses_a_package_that_is_not_there(self):

        ref = self.save()
        with self.assertRaises(ToolError) as caught:
            mcp_server.approve_package(ref)
        self.assertIn("no package", str(caught.exception))

    def test_the_answer_tool_adds_one(self):

        (self.home / "resumes").mkdir(parents=True, exist_ok=True)
        (self.home / "resumes" / "master.md").write_text(MASTER, encoding="utf-8")
        ref = self.save()
        with db.connect() as connection:
            tailoring.tailor(connection, ref, FakeProvider())
        reply = mcp_server.add_answer(ref, "Why us?", "Because.")
        self.assertIn("Not checked", reply)
        self.assertIn("Because.", mcp_server.get_package(ref))


class Postings(InAScratchHome):
    def test_deleting_a_posting_takes_its_package_with_it(self):
        (self.home / "resumes").mkdir(parents=True, exist_ok=True)
        (self.home / "resumes" / "master.md").write_text(MASTER, encoding="utf-8")
        ref = self.save()
        with db.connect() as connection:
            tailoring.tailor(connection, ref, FakeProvider())
            packages.add_answer(connection, ref, "Why us?", "Because.")
            posting = postings.read(connection, ref)
            connection.execute("DELETE FROM postings WHERE id = ?", (posting.id,))
            left = connection.execute("SELECT COUNT(*) AS n FROM answers").fetchone()
        self.assertEqual(left["n"], 0)


class Scanning(InAScratchHome):
    """What the package says about text it can only scan."""

    def setUp(self):
        super().setUp()
        (self.home / "resumes").mkdir(parents=True, exist_ok=True)
        (self.home / "resumes" / "master.md").write_text(MASTER, encoding="utf-8")
        self.ref = self.save()
        with db.connect() as connection:
            tailoring.tailor(connection, self.ref, FakeProvider())

    def _render(self, answer):
        with db.connect() as connection:
            packages.add_answer(connection, self.ref, "Why us?", answer)
            return packages.read(connection, self.ref).render()

    def test_an_answer_with_nothing_flagged_is_not_called_checked(self):
        # The weaker claim has to read like one. "Nothing flagged" is not
        # "verified", and a package that blurs them is the failure this whole
        # feature exists to avoid.
        rendered = self._render("I ran the Postgres upgrade and liked it.")
        self.assertIn("scanned, nothing flagged", rendered)
        self.assertNotIn("Why us?  [checked]", rendered)

    def test_a_flagged_answer_counts_what_it_found(self):
        rendered = self._render("I am an expert in Kubernetes and in Fortran.")
        self.assertIn("scanned, 2 to check", rendered)

    def test_the_resume_keeps_its_stronger_verdict(self):
        rendered = self._render("I am an expert in Kubernetes.")
        self.assertIn("Resume, version 1  [checked]", rendered)

    def test_a_package_with_no_master_resume_still_renders(self):
        # It cannot scan without one, but showing what is about to be sent is
        # more use than refusing to render at all.
        with db.connect() as connection:
            packages.add_answer(connection, self.ref, "Why us?", "Anything.")
        (self.home / "resumes" / "master.md").unlink()
        with db.connect() as connection:
            rendered = packages.read(connection, self.ref).render()
        self.assertIn("Why us?", rendered)
