"""CLI paths the Gherkin does not reach, and the ones it would contort to."""

import io
import unittest.mock

from support import InAScratchHome

from scout import applications, db, postings


class Init(InAScratchHome):
    def test_it_says_every_file_it_wrote(self):
        code, output = self.run_cli("init")
        self.assertEqual(code, 0, output)
        self.assertIn("resumes/master.example.md", output)
        self.assertIn("resumes/master.md", output)
        self.assertTrue((self.home / "resumes" / "master.md").exists())

    def test_it_does_not_overwrite_a_master_resume(self):
        self.run_cli("init")
        (self.home / "resumes" / "master.md").write_text("mine", encoding="utf-8")
        code, output = self.run_cli("init")
        self.assertEqual(code, 0, output)
        # The whole point: a setup step that silently ate somebody's resume
        # would be worse than no setup step at all.
        self.assertIn("already there", output)
        self.assertEqual(
            (self.home / "resumes" / "master.md").read_text(encoding="utf-8"), "mine"
        )


class Saving(InAScratchHome):
    def test_a_posting_can_be_piped_in(self):
        with unittest.mock.patch("sys.stdin", io.StringIO("Staff Engineer at Orrery")):
            code, output = self.run_cli("save", "--text", "-")
        self.assertEqual(code, 0, output)

    def test_two_postings_at_one_company_get_different_references(self):
        first = self.save(title="Staff Engineer", company="Orrery")
        second = self.save(title="Staff Engineer", company="Orrery")
        self.assertNotEqual(first, second)
        self.assertTrue(second.endswith("-2"), second)

    def test_a_posting_with_no_title_or_company_still_gets_a_reference(self):
        code, output = self.run_cli("save", "--text", "A job, somewhere.")
        self.assertEqual(code, 0, output)
        self.assertIn("Saved posting", output)


class Editing(InAScratchHome):
    def test_setting_the_company_scout_would_not_guess(self):
        code, output = self.run_cli("save", "--text", "A job, somewhere.")
        ref = output.splitlines()[0].removeprefix("Saved ").strip()
        code, output = self.run_cli("edit", ref, "--company", "Orrery")
        self.assertEqual(code, 0, output)
        _, output = self.run_cli("show", ref)
        self.assertIn("company  Orrery", output)

    def test_editing_nothing_is_refused(self):
        ref = self.save()
        code, output = self.run_cli("edit", ref)
        self.assertEqual(code, 1)
        self.assertIn("Nothing to change", output)

    def test_setting_only_the_title_keeps_the_company(self):
        ref = self.save()
        self.run_cli("edit", ref, "--title", "Principal Engineer")
        _, output = self.run_cli("show", ref)
        self.assertIn("Principal Engineer", output)
        self.assertIn("company  Orrery", output)


class Listing(InAScratchHome):
    def test_an_empty_list_says_what_to_do_next(self):
        code, output = self.run_cli("list")
        self.assertEqual(code, 0, output)
        self.assertIn("Nothing saved yet", output)

    def test_a_posting_with_no_title_lists_as_untitled(self):
        self.run_cli("save", "--text", "A job, somewhere.")
        _, output = self.run_cli("list")
        self.assertIn("(untitled)", output)


class Notes(InAScratchHome):
    def test_a_note_against_a_posting_that_is_not_there(self):
        code, output = self.run_cli("note", "no-such-posting", "anything")
        self.assertEqual(code, 1)
        self.assertIn("no posting called", output)


class TheMcpSubcommand(InAScratchHome):
    def test_it_runs_the_server(self):
        # The server itself is covered by features/mcp.feature, over a real
        # pipe. What is covered here is only that this subcommand reaches it.
        with unittest.mock.patch("scout.mcp_server.main", return_value=0) as served:
            code, _ = self.run_cli("mcp")
        self.assertEqual(code, 0)
        served.assert_called_once()


class Statuses(InAScratchHome):
    def test_the_url_of_a_pasted_posting_is_not_shown(self):
        ref = self.save()
        _, output = self.run_cli("show", ref)
        self.assertNotIn("url ", output)

    def test_an_ending_is_reachable_from_the_beginning(self):
        ref = self.save()
        code, output = self.run_cli("log", ref, "ghosted", "--note", "nothing, ever")
        self.assertEqual(code, 0, output)

    def test_a_posting_cannot_go_back_to_saved(self):
        ref = self.save()
        self.run_cli("log", ref, "ghosted")
        code, output = self.run_cli("log", ref, "saved")
        self.assertEqual(code, 1)
        self.assertIn('From "ghosted" you can log', output)


class Transitions(unittest.TestCase):
    def test_offer_can_only_end(self):
        self.assertEqual(applications.allowed_from("offer"), applications.ENDINGS)

    def test_an_ending_returns_to_the_path_but_not_to_saved(self):
        self.assertNotIn("saved", applications.allowed_from("rejected"))
        self.assertIn("screening", applications.allowed_from("rejected"))


class Rollback(InAScratchHome):
    def test_a_failed_transaction_leaves_nothing_behind(self):
        with self.assertRaises(RuntimeError), db.connect() as connection:
            postings.save(connection, text="A job, somewhere.")
            raise RuntimeError("something went wrong after the insert")
        with db.connect() as connection:
            self.assertEqual(postings.all_postings(connection), [])
