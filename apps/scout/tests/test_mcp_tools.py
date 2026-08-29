"""The MCP tools' own branches.

The transport, the handshake and the process are covered by
features/mcp.feature over a real pipe. What is left here is the argument
handling inside each tool, which that suite would need a scenario apiece to
reach.
"""

from mcp.server.mcpserver.exceptions import ToolError
from support import InAScratchHome

from scout import mcp_server


class SavePosting(InAScratchHome):
    def test_neither_a_url_nor_text(self):
        with self.assertRaises(ToolError) as caught:
            mcp_server.save_posting()
        self.assertIn("exactly one", str(caught.exception))

    def test_both_a_url_and_text(self):
        with self.assertRaises(ToolError) as caught:
            mcp_server.save_posting(url="https://example.com/1", text="a posting")
        self.assertIn("exactly one", str(caught.exception))

    def test_an_unknown_company_is_said_out_loud(self):
        reply = mcp_server.save_posting(text="A job, somewhere, in Python.")
        self.assertIn("company is unknown", reply)

    def test_a_named_company_is_not_remarked_on(self):
        reply = mcp_server.save_posting(
            text="A job in Python.", title="Staff Engineer", company="Orrery"
        )
        self.assertNotIn("company is unknown", reply)


class ListPostings(InAScratchHome):
    def test_nothing_saved_yet(self):
        self.assertEqual(mcp_server.list_postings(), "Nothing saved yet.")

    def test_it_lists_what_is_there(self):
        self.save(title="Staff Engineer", company="Orrery")
        listed = mcp_server.list_postings()
        self.assertIn("Staff Engineer", listed)
        self.assertIn("saved", listed)

    def test_it_can_hide_what_ended(self):
        ref = self.save(title="Staff Engineer", company="Orrery")
        mcp_server.log_status(ref, "ghosted")
        self.assertEqual(
            mcp_server.list_postings(in_play_only=True), "Nothing saved yet."
        )


class TailorResume(InAScratchHome):
    def test_a_posting_that_is_not_there(self):
        with self.assertRaises(ToolError) as caught:
            mcp_server.tailor_resume(ref="no-such-posting", provider="fake")
        self.assertIn("no posting called", str(caught.exception))
