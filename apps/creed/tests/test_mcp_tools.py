"""Every tool on the server, called in process.

The MCP specs prove the pipe works — that a real client can start a real
server and get real frames back. These cover the branches inside each tool,
which a subprocess is an expensive way to reach.
"""

from mcp.server.mcpserver.exceptions import ToolError
from scratch import CreedTestCase

from creed import db, mcp_server


class TestLookupTools(CreedTestCase):
    def test_search(self):
        self.assertIn("Testudo Walker", mcp_server.search_datasheets("walker"))

    def test_search_within_a_faction(self):
        reply = mcp_server.search_datasheets("Testudo", faction="Test Xenos")
        self.assertNotIn("Testudo Walker", reply)

    def test_search_with_an_empty_query(self):
        with self.assertRaises(ToolError):
            mcp_server.search_datasheets("   ")

    def test_get_by_id(self):
        self.assertIn("Statlines", mcp_server.get_datasheet("D1"))

    def test_get_by_exact_name(self):
        self.assertIn("Statlines", mcp_server.get_datasheet("Testudo Walker"))

    def test_get_by_a_partial_name(self):
        self.assertIn("Testudo Walker", mcp_server.get_datasheet("Walk"))

    def test_a_shared_name_offers_the_choices(self):
        with self.assertRaises(ToolError) as caught:
            mcp_server.get_datasheet("Testudo Guard")
        self.assertIn("Test Xenos", str(caught.exception))

    def test_a_shared_name_with_a_faction(self):
        reply = mcp_server.get_datasheet("Testudo Guard", faction="Test Guard")
        self.assertIn("Testudo Sergeant", reply)

    def test_a_partial_name_matching_several_offers_the_choices(self):
        with self.assertRaises(ToolError) as caught:
            mcp_server.get_datasheet("Testudo")
        self.assertIn("Did you mean", str(caught.exception))

    def test_nothing_at_all(self):
        with self.assertRaises(ToolError) as caught:
            mcp_server.get_datasheet("Breakfast Cereal")
        self.assertIn("Nothing matched", str(caught.exception))

    def test_factions(self):
        self.assertIn("Test Guard", mcp_server.list_factions())

    def test_stratagems(self):
        self.assertIn("BRACE", mcp_server.find_stratagems(turn="Your turn"))

    def test_stratagems_with_a_phase_that_is_not_one(self):
        with self.assertRaises(ToolError) as caught:
            mcp_server.find_stratagems(phase="Breakfast phase")
        self.assertIn("Shooting phase", str(caught.exception))

    def test_stratagems_matching_nothing(self):
        self.assertIn("No stratagems", mcp_server.find_stratagems(name="NOTHING"))

    def test_detachment_by_name(self):
        reply = mcp_server.get_detachment(name="Shield Doctrine")
        self.assertIn("Hold The Line", reply)

    def test_detachment_with_per_chapter_points(self):
        reply = mcp_server.get_detachment(name="Spear Doctrine")
        self.assertIn("differ by chapter", reply)

    def test_detachments_for_a_faction(self):
        self.assertIn(
            "Shield Doctrine", mcp_server.get_detachment(faction="Test Guard")
        )

    def test_detachment_with_neither_argument(self):
        with self.assertRaises(ToolError):
            mcp_server.get_detachment()

    def test_a_detachment_that_does_not_exist(self):
        with self.assertRaises(ToolError):
            mcp_server.get_detachment(name="Breakfast Doctrine")

    def test_a_faction_with_no_detachments(self):
        with self.assertRaises(ToolError):
            mcp_server.get_detachment(faction="Nobody")

    def test_freshness(self):
        self.assertIn("Export last updated", mcp_server.data_freshness())


class TestListTools(CreedTestCase):
    def _start(self, name="mcp", points=2000):
        reply = mcp_server.start_list(name, "Test Guard", points)
        return int(reply.rsplit("list_id is ", 1)[1].rstrip("."))

    def test_the_whole_flow(self):
        list_id = self._start()
        added = mcp_server.add_unit(list_id, "D1", 5)
        self.assertIn("Added", added)
        unit_id = int(added.rsplit("unit_id is ", 1)[1].split(".")[0])
        self.assertIn("Detachment set", mcp_server.set_detachment(list_id, "DT1"))
        self.assertIn("Total:", mcp_server.show_list(list_id))
        self.assertIn("Not checked", mcp_server.check_list(list_id))
        self.assertIn("Removed", mcp_server.remove_unit(list_id, unit_id))

    def test_the_tier_is_named_when_it_escalates(self):
        list_id = self._start()
        mcp_server.add_unit(list_id, "D1", 5)
        mcp_server.add_unit(list_id, "D1", 5)
        third = mcp_server.add_unit(list_id, "D1", 5)
        self.assertIn("your 3+ of this datasheet", third)

    def test_going_over_says_so(self):
        list_id = self._start(name="small", points=50)
        self.assertIn("over its limit", mcp_server.add_unit(list_id, "D1", 5))

    def test_a_duplicate_name(self):
        self._start(name="twice")
        with self.assertRaises(ToolError):
            mcp_server.start_list("twice", "Test Guard", 2000)

    def test_a_faction_that_does_not_exist(self):
        with self.assertRaises(ToolError):
            mcp_server.start_list("x", "Nobody", 2000)

    def test_a_size_it_does_not_come_in(self):
        list_id = self._start()
        with self.assertRaises(ToolError) as caught:
            mcp_server.add_unit(list_id, "D1", 7)
        self.assertIn("5, 10", str(caught.exception))

    def test_adding_something_that_does_not_exist(self):
        list_id = self._start()
        with self.assertRaises(ToolError):
            mcp_server.add_unit(list_id, "Breakfast Cereal")

    def test_removing_something_that_is_not_there(self):
        list_id = self._start()
        with self.assertRaises(ToolError):
            mcp_server.remove_unit(list_id, 999)

    def test_a_detachment_from_another_faction(self):
        list_id = self._start()
        with self.assertRaises(ToolError):
            mcp_server.set_detachment(list_id, "Alien Doctrine")

    def test_showing_every_list(self):
        self._start(name="one")
        self._start(name="two")
        reply = mcp_server.show_list()
        self.assertIn("one", reply)
        self.assertIn("two", reply)

    def test_showing_when_there_are_none(self):
        self.assertIn("No lists yet", mcp_server.show_list())

    def test_showing_one_that_is_not_there(self):
        with self.assertRaises(ToolError):
            mcp_server.show_list(999)

    def test_checking_one_that_is_not_there(self):
        with self.assertRaises(ToolError):
            mcp_server.check_list(999)

    def test_a_check_never_says_legal(self):
        list_id = self._start()
        mcp_server.add_unit(list_id, "D1", 5)
        mcp_server.set_detachment(list_id, "DT1")
        reply = mcp_server.check_list(list_id)
        self.assertNotIn("is legal", reply.replace("being legal", ""))


class TestAttackTool(CreedTestCase):
    def test_one_weapon(self):
        reply = mcp_server.work_out_attack("D2", "D3", weapon="Test blade")
        self.assertIn("Expected damage", reply)

    def test_every_weapon_when_none_is_named(self):
        reply = mcp_server.work_out_attack("D2", "D3")
        self.assertIn("Test blade", reply)

    def test_a_weapon_it_does_not_have(self):
        with self.assertRaises(ToolError):
            mcp_server.work_out_attack("D2", "D3", weapon="Spoon")

    def test_a_target_with_no_model_profile(self):
        with db.session() as connection:
            connection.execute(
                "DELETE FROM Datasheets_models WHERE datasheet_id = 'D3'"
            )
        with self.assertRaises(ToolError):
            mcp_server.work_out_attack("D2", "D3")

    def test_a_profile_creed_cannot_read(self):
        with db.session() as connection:
            connection.execute(
                "UPDATE Datasheets_wargear SET A = 'lots' WHERE name = 'Test blade'"
            )
        reply = mcp_server.work_out_attack("D2", "D3", weapon="Test blade")
        self.assertIn("could not read", reply)


class TestBeforeAnySync(CreedTestCase):
    sync_on_setup = False

    def test_every_read_tool_says_to_sync(self):
        for call in (
            lambda: mcp_server.search_datasheets("x"),
            lambda: mcp_server.get_datasheet("D1"),
            lambda: mcp_server.list_factions(),
            lambda: mcp_server.find_stratagems(),
            lambda: mcp_server.get_detachment(name="x"),
            lambda: mcp_server.show_list(),
            lambda: mcp_server.check_list(1),
            lambda: mcp_server.work_out_attack("a", "b"),
            lambda: mcp_server.start_list("x", "y", 1),
            lambda: mcp_server.add_unit(1, "x"),
            lambda: mcp_server.remove_unit(1, 1),
            lambda: mcp_server.set_detachment(1, "x"),
            lambda: mcp_server.data_freshness(),
        ):
            with self.assertRaises(ToolError):
                call()


class TestStartupSync(CreedTestCase):
    sync_on_setup = False

    def test_it_syncs(self):
        mcp_server._sync_on_start()
        self.assertIn("Export last updated", mcp_server.data_freshness())

    def test_it_can_be_skipped(self):
        import os

        os.environ["CREED_SYNC_ON_START"] = "0"
        try:
            mcp_server._sync_on_start()
        finally:
            os.environ.pop("CREED_SYNC_ON_START", None)
        with self.assertRaises(ToolError):
            mcp_server.data_freshness()

    def test_an_unreachable_export_does_not_stop_the_server(self):
        self.site.offline = True
        mcp_server._sync_on_start()

    def test_a_failing_sync_does_not_stop_the_server(self):
        self.site.fail_after = 2
        mcp_server._sync_on_start()

    def test_already_current_is_reported(self):
        mcp_server._sync_on_start()
        mcp_server._sync_on_start()


class TestServerEntryPoint(CreedTestCase):
    sync_on_setup = False

    def test_main_configures_logging_and_runs(self):
        import os
        import unittest.mock

        os.environ["CREED_SYNC_ON_START"] = "0"
        try:
            with unittest.mock.patch.object(mcp_server.server, "run") as run:
                self.assertEqual(mcp_server.main(), 0)
            run.assert_called_once_with("stdio")
        finally:
            os.environ.pop("CREED_SYNC_ON_START", None)
