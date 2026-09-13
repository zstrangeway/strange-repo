"""Every subcommand and every refusal the command line can produce."""

import contextlib
import io

from scratch import CreedTestCase

from creed import army, cli, datasheets, db


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(list(argv))
        except SystemExit as exit_code:
            code = int(exit_code.code or 0)
    return code, out.getvalue(), err.getvalue()


class TestReading(CreedTestCase):
    def test_search(self):
        code, out, _ = run("search", "Testudo")
        self.assertEqual(code, 0)
        self.assertIn("Testudo Guard", out)

    def test_search_within_a_faction(self):
        code, out, _ = run("search", "Testudo", "--faction", "Test Xenos")
        self.assertEqual(code, 0)
        self.assertNotIn("Testudo Walker", out)

    def test_search_matching_nothing_exits_non_zero(self):
        code, out, _ = run("search", "Breakfast Cereal")
        self.assertEqual(code, 1)
        self.assertIn("Nothing matched", out)

    def test_show_by_name(self):
        code, out, _ = run("show", "Testudo Walker")
        self.assertEqual(code, 0)
        self.assertIn("Statlines", out)
        self.assertIn("Damaged", out)

    def test_show_a_shared_name_refuses_and_lists_the_factions(self):
        code, out, _ = run("show", "Testudo Guard")
        self.assertEqual(code, 1)
        self.assertIn("Test Guard", out)
        self.assertIn("Test Xenos", out)

    def test_show_a_shared_name_with_a_faction(self):
        code, _, _ = run("show", "Testudo Guard", "--faction", "Test Guard")
        self.assertEqual(code, 0)

    def test_show_falls_back_to_a_search(self):
        code, out, _ = run("show", "Walk")
        self.assertEqual(code, 0)
        self.assertIn("Testudo Walker", out)

    def test_show_nothing_at_all(self):
        code, out, _ = run("show", "Breakfast Cereal")
        self.assertEqual(code, 1)
        self.assertIn("Nothing matched", out)

    def test_factions(self):
        code, out, _ = run("factions")
        self.assertEqual(code, 0)
        self.assertIn("Test Guard", out)

    def test_stratagems_with_no_filters(self):
        code, out, _ = run("stratagems")
        self.assertEqual(code, 0)
        self.assertIn("BRACE", out)

    def test_stratagems_with_a_phase_that_is_one(self):
        code, out, _ = run("stratagems", "--phase", "Shooting phase")
        self.assertEqual(code, 0)
        self.assertIn("BRACE", out)

    def test_stratagems_matching_nothing(self):
        code, _, _ = run("stratagems", "--name", "NOTHING")
        self.assertEqual(code, 1)

    def test_stratagems_with_a_phase_that_is_not_one(self):
        code, _, err = run("stratagems", "--phase", "Breakfast phase")
        self.assertEqual(code, 1)
        self.assertIn("Shooting phase", err)

    def test_detachments_for_a_faction(self):
        code, out, _ = run("detachments", "--faction", "Test Guard")
        self.assertEqual(code, 0)
        self.assertIn("Shield Doctrine", out)

    def test_detachments_for_a_faction_with_none(self):
        code, _, err = run("detachments", "--faction", "Nobody")
        self.assertEqual(code, 1)
        self.assertIn("no detachments", err)

    def test_one_detachment_by_name(self):
        code, out, _ = run("detachments", "--name", "Shield Doctrine")
        self.assertEqual(code, 0)
        self.assertIn("Hold The Line", out)
        self.assertIn("Take and Hold", out)

    def test_a_detachment_that_does_not_exist(self):
        code, _, err = run("detachments", "--name", "Breakfast Doctrine")
        self.assertEqual(code, 1)
        self.assertIn("no detachment matched", err)


class TestAttack(CreedTestCase):
    def test_one_weapon(self):
        code, out, _ = run(
            "attack", "Testudo Captain", "Testudo Walker", "--weapon", "Test blade"
        )
        self.assertEqual(code, 0)
        self.assertIn("Expected damage", out)

    def test_every_weapon_when_none_is_named(self):
        code, out, _ = run("attack", "Testudo Captain", "Testudo Walker")
        self.assertEqual(code, 0)
        self.assertIn("Test blade", out)

    def test_an_attacker_that_does_not_exist(self):
        code, _, err = run("attack", "Nobody", "Testudo Walker")
        self.assertEqual(code, 1)
        self.assertIn("no datasheet called", err)

    def test_a_target_that_does_not_exist(self):
        code, _, err = run("attack", "Testudo Captain", "Nobody")
        self.assertEqual(code, 1)
        self.assertIn("no datasheet called", err)

    def test_a_weapon_the_attacker_does_not_have(self):
        code, _, err = run(
            "attack", "Testudo Captain", "Testudo Walker", "--weapon", "Spoon"
        )
        self.assertEqual(code, 1)
        self.assertIn("Test blade", err)

    def test_a_profile_creed_cannot_read(self):
        with db.session() as connection:
            connection.execute(
                "UPDATE Datasheets_wargear SET A = 'lots' WHERE name = 'Test blade'"
            )
        code, out, _ = run(
            "attack", "Testudo Captain", "Testudo Walker", "--weapon", "Test blade"
        )
        self.assertEqual(code, 0)
        self.assertIn("could not read", out)

    def test_a_target_with_no_model_profile(self):
        with db.session() as connection:
            connection.execute(
                "DELETE FROM Datasheets_models WHERE datasheet_id = 'D3'"
            )
        code, _, err = run("attack", "Testudo Captain", "Testudo Walker")
        self.assertEqual(code, 1)
        self.assertIn("no model profile", err)


class TestLists(CreedTestCase):
    def _start(self, name="cli", points=2000):
        run("list", "new", name, "Test Guard", "--points", str(points))
        with db.session() as connection:
            return army.all_lists(connection)[-1]["id"]

    def test_the_whole_flow(self):
        list_id = self._start()
        code, out, _ = run("list", "add", str(list_id), "D1", "--models", "5")
        self.assertEqual(code, 0)
        self.assertIn("Added", out)
        code, out, _ = run("list", "detachment", str(list_id), "Shield Doctrine")
        self.assertEqual(code, 0)
        code, out, _ = run("list", "show", str(list_id))
        self.assertIn("Total:", out)
        code, out, _ = run("list", "check", str(list_id))
        self.assertEqual(code, 0)
        self.assertIn("Not checked", out)

    def test_listing_every_list(self):
        self._start("one")
        self._start("two")
        code, out, _ = run("list", "show")
        self.assertEqual(code, 0)
        self.assertIn("one", out)
        self.assertIn("two", out)

    def test_no_lists_at_all(self):
        code, out, _ = run("list", "show")
        self.assertEqual(code, 1)
        self.assertIn("No lists yet", out)

    def test_a_duplicate_name_is_refused(self):
        self._start("same")
        code, _, err = run("list", "new", "same", "Test Guard")
        self.assertEqual(code, 1)
        self.assertIn("already exists", err)

    def test_a_faction_that_does_not_exist(self):
        code, _, err = run("list", "new", "x", "Nobody")
        self.assertEqual(code, 1)
        self.assertIn("no faction", err)

    def test_adding_by_an_ambiguous_name(self):
        list_id = self._start()
        code, _, err = run("list", "add", str(list_id), "Testudo Guard")
        self.assertEqual(code, 1)
        self.assertIn("Pass an id", err)

    def test_adding_by_name_with_a_faction(self):
        list_id = self._start()
        code, _, _ = run(
            "list", "add", str(list_id), "Testudo Guard", "--faction", "Test Guard"
        )
        self.assertEqual(code, 0)

    def test_adding_by_a_partial_name(self):
        list_id = self._start()
        code, out, _ = run("list", "add", str(list_id), "Walk")
        self.assertEqual(code, 0)
        self.assertIn("Testudo Walker", out)

    def test_adding_something_that_does_not_exist(self):
        list_id = self._start()
        code, _, err = run("list", "add", str(list_id), "Breakfast Cereal")
        self.assertEqual(code, 1)
        self.assertIn("no datasheet matched", err)

    def test_adding_at_a_size_it_does_not_come_in(self):
        list_id = self._start()
        code, _, err = run("list", "add", str(list_id), "D1", "--models", "7")
        self.assertEqual(code, 1)
        self.assertIn("5, 10", err)

    def test_going_over_the_limit_warns_but_adds(self):
        list_id = self._start(name="small", points=50)
        code, out, _ = run("list", "add", str(list_id), "D1", "--models", "5")
        self.assertEqual(code, 0)
        self.assertIn("over its limit", out)

    def test_removing(self):
        list_id = self._start()
        run("list", "add", str(list_id), "D1", "--models", "5")
        with db.session() as connection:
            unit_id = army.price(connection, list_id).units[0].id
        code, out, _ = run("list", "remove", str(list_id), str(unit_id))
        self.assertEqual(code, 0)
        self.assertIn("Removed", out)

    def test_removing_something_that_is_not_there(self):
        list_id = self._start()
        code, _, err = run("list", "remove", str(list_id), "999")
        self.assertEqual(code, 1)
        self.assertIn("no unit", err)

    def test_a_detachment_from_another_faction(self):
        list_id = self._start()
        code, _, err = run("list", "detachment", str(list_id), "Alien Doctrine")
        self.assertEqual(code, 1)
        self.assertIn("Shield Doctrine", err)

    def test_a_detachment_that_does_not_exist(self):
        list_id = self._start()
        code, _, err = run("list", "detachment", str(list_id), "Nothing")
        self.assertEqual(code, 1)
        self.assertIn("no detachment", err)

    def test_showing_a_list_that_is_not_there(self):
        code, _, err = run("list", "show", "999")
        self.assertEqual(code, 1)
        self.assertIn("no list", err)

    def test_checking_a_list_that_is_not_there(self):
        code, _, _ = run("list", "check", "999")
        self.assertEqual(code, 1)

    def test_a_failing_check_exits_non_zero(self):
        list_id = self._start(name="bad", points=10)
        run("list", "add", str(list_id), "D1", "--models", "5")
        code, out, _ = run("list", "check", str(list_id))
        self.assertEqual(code, 1)
        self.assertIn("Problems", out)


class TestSyncCommands(CreedTestCase):
    def test_status(self):
        code, out, _ = run("status")
        self.assertEqual(code, 0)
        self.assertIn("Rows held", out)

    def test_sync_when_already_current(self):
        code, out, _ = run("sync")
        self.assertEqual(code, 0)
        self.assertIn("Already current", out)

    def test_forced_sync_reports_what_it_did(self):
        code, out, _ = run("sync", "--force")
        self.assertEqual(code, 0)
        self.assertIn("unchanged", out)

    def test_a_sync_that_fails_leaves_the_data_alone(self):
        self.site.set_last_update("2030-01-01 00:00:00")
        self.site.fail_after = 3
        code, _, err = run("sync")
        self.assertEqual(code, 1)
        self.assertIn("previous data is untouched", err)
        with db.session() as connection:
            self.assertTrue(datasheets.by_name(connection, "Testudo Walker"))

    def test_a_sync_with_the_export_unreachable(self):
        self.site.offline = True
        code, _, err = run("sync")
        self.assertEqual(code, 1)
        self.assertIn("could not reach", err)


class TestBeforeAnySync(CreedTestCase):
    sync_on_setup = False

    def test_status_says_to_sync(self):
        code, _, err = run("status")
        self.assertEqual(code, 1)
        self.assertIn("creed sync", err)

    def test_a_lookup_says_to_sync(self):
        code, _, err = run("show", "Testudo Guard")
        self.assertEqual(code, 1)
        self.assertIn("creed sync", err)

    def test_starting_a_list_says_to_sync(self):
        code, _, err = run("list", "new", "x", "Test Guard")
        self.assertEqual(code, 1)
        self.assertIn("creed sync", err)

    def test_a_first_sync_reports_rows(self):
        code, out, _ = run("sync")
        self.assertEqual(code, 0)
        self.assertIn("rows across", out)
