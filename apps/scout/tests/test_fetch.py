"""Fetching a posting, at the failures a local board cannot stage."""

import unittest
import unittest.mock

import httpx

from scout import fetch
from scout.errors import ScoutError


class Failures(unittest.TestCase):
    def _raising(self, error):
        return unittest.mock.patch("scout.fetch.httpx.get", side_effect=error)

    def test_a_connection_that_never_opens(self):
        # Distinct from a timeout: there is no board at the other end at all,
        # which is what a typo in a URL looks like.
        with (
            self._raising(httpx.ConnectError("nodename nor servname provided")),
            self.assertRaises(ScoutError) as caught,
        ):
            fetch.posting_from_url("https://nowhere.example/jobs/1")
        self.assertIn("Could not reach", str(caught.exception))
        self.assertIn("Paste the text instead", caught.exception.detail)

    def test_a_timeout_says_how_long_it_waited(self):
        with (
            self._raising(httpx.ReadTimeout("too slow")),
            self.assertRaises(ScoutError) as caught,
        ):
            fetch.posting_from_url("https://slow.example/jobs/1", timeout=2)
        self.assertIn("2s", str(caught.exception))


class Extraction(unittest.TestCase):
    def test_a_page_trafilatura_cannot_read_at_all(self):
        # extract() returns None rather than raising, and an unguarded None
        # would be saved as the posting.
        response = httpx.Response(200, text="<html><body></body></html>")
        with (
            unittest.mock.patch("scout.fetch.httpx.get", return_value=response),
            self.assertRaises(ScoutError) as caught,
        ):
            fetch.posting_from_url("https://empty.example/jobs/1")
        self.assertIn("no readable posting", str(caught.exception))

    def test_a_page_with_no_title_metadata_still_saves(self):
        # Two paragraphs, because one repeated line is one sentence, and a
        # page with one sentence in it is an index rather than a posting —
        # which the listing check below is right to say.
        body = (
            "<html><body><article>"
            "<p>We are looking for a platform engineer to own the deploy "
            "pipeline end to end, and to keep it fast enough that nobody "
            "batches their changes up.</p>"
            "<p>You would work in Python against Postgres, with Terraform "
            "describing every environment underneath it.</p>"
            "<p>" + ("More about the role. " * 20) + "</p>"
            "</article></body></html>"
        )
        response = httpx.Response(200, text=body)
        with (
            unittest.mock.patch("scout.fetch.httpx.get", return_value=response),
            unittest.mock.patch(
                "scout.fetch.trafilatura.extract_metadata", return_value=None
            ),
        ):
            text, title = fetch.posting_from_url("https://plain.example/jobs/1")
        self.assertIsNone(title)
        self.assertIn("platform engineer", text)


class ListingPages(unittest.TestCase):
    """A board's index is long, extracts cleanly, and is not a job.

    Found by pointing scout at a real Greenhouse board. Length alone does not
    tell the two apart — prose does.
    """

    @staticmethod
    def _page(body):
        return httpx.Response(
            200, text=f"<html><body><article>{body}</article></body></html>"
        )

    def _save(self, body):
        with unittest.mock.patch(
            "scout.fetch.httpx.get", return_value=self._page(body)
        ):
            return fetch.posting_from_url("https://board.example/jobs")

    def test_a_list_of_titles_and_locations_is_refused(self):
        listing = "".join(
            f"<p>Staff Engineer {n} — London, United Kingdom, Engineering</p>"
            for n in range(30)
        )
        with self.assertRaises(ScoutError) as caught:
            self._save(listing)
        self.assertIn("list of jobs", str(caught.exception))
        self.assertIn("Open the posting itself", caught.exception.detail)

    def test_one_marketing_sentence_does_not_make_an_index_a_posting(self):
        # The real Greenhouse index had exactly one, which is why the bar sits
        # above one rather than above zero.
        listing = (
            "<p>Level up your career by having opportunities sent to your "
            "inbox today.</p>"
        )
        listing += "".join(
            f"<p>Staff Engineer {n} — London, United Kingdom</p>" for n in range(30)
        )
        with self.assertRaises(ScoutError) as caught:
            self._save(listing)
        self.assertIn("list of jobs", str(caught.exception))

    def test_a_terse_posting_is_still_saved(self):
        # Two sentences is a thin job description, not a board index, and
        # refusing it would be scout deciding it knows better.
        posting = (
            "<p>" + "We are looking for a platform engineer to own our deploy "
            "pipeline end to end and keep it fast." + "</p>"
            "<p>" + "You would work in Python against Postgres, with Terraform "
            "describing the infrastructure underneath it." + "</p>"
            "<p>" + "x" * 400 + "</p>"
        )
        text, _ = self._save(posting)
        self.assertIn("platform engineer", text)
