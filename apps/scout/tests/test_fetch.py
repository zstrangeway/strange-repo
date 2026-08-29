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
        body = (
            "<html><body><article><p>"
            + ("A real posting. " * 60)
            + "</p></article></body></html>"
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
        self.assertIn("A real posting.", text)
