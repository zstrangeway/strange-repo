"""The importer's verifier, which is the whole of why a model is allowed near
the master resume."""

import unittest
import unittest.mock

from support import InAScratchHome

from scout import importer
from scout.errors import ScoutError
from scout.providers.fake import FakeProvider

RESUME = "Ada Lovelace\n\nSkills: Python, Postgres\n\nWilding Labs - Engineer 2021\n"


class Verifying(unittest.TestCase):
    def test_markdown_around_the_same_words_is_no_change(self):
        markdown = "# Ada Lovelace\n\n## Skills\n\n- Python, Postgres\n"
        lost, invented = importer.verify(
            "Ada Lovelace\nSkills\nPython, Postgres\n", markdown
        )
        self.assertEqual((lost, invented), ([], []))

    def test_a_dropped_word_is_caught(self):
        lost, invented = importer.verify(RESUME, RESUME.replace("Postgres", ""))
        self.assertEqual(lost, ["postgres"])
        self.assertEqual(invented, [])

    def test_an_invented_word_is_caught(self):
        lost, invented = importer.verify(
            RESUME, RESUME.replace("Python", "Python, Rust")
        )
        self.assertEqual(lost, [])
        self.assertEqual(invented, ["rust"])

    def test_a_reworded_line_is_caught_both_ways(self):
        # The tightest guarantee scout makes anywhere: an importer may not
        # rewrite, so a reword shows up as both a loss and an invention.
        lost, invented = importer.verify(
            RESUME, RESUME.replace("Engineer", "Architect")
        )
        self.assertEqual(lost, ["engineer"])
        self.assertEqual(invented, ["architect"])

    def test_hash_marks_are_markdown_and_not_words(self):
        # The markers themselves are not counted; the words beside them are.
        lost, invented = importer.verify("Ada\n", "# Ada\n")
        self.assertEqual((lost, invented), ([], []))
        lost, invented = importer.verify("Ada\n", "### Ada\n")
        self.assertEqual((lost, invented), ([], []))

    def test_a_language_called_c_sharp_is_a_word(self):
        lost, invented = importer.verify("C#\n", "## Skills\n\n- C#\n")
        self.assertEqual((lost, invented), ([], ["skills"]))

    def test_a_running_header_may_be_dropped(self):
        # Repeated on every page, so the model is right to drop the repeats.
        source = "Ada Lovelace\n1\nbody\nAda Lovelace\n2\nmore\nAda Lovelace\n3\n"
        lost, invented = importer.verify(source, "# Ada Lovelace\n\nbody\n\nmore\n")
        self.assertEqual((lost, invented), ([], []))

    def test_the_first_occurrence_of_a_repeated_line_is_content(self):
        # Dropping all six copies would make the name at the top of page one
        # read as something the importer invented.
        source = "Ada Lovelace\nbody\nAda Lovelace\nAda Lovelace\n"
        lost, _ = importer.verify(source, "body\n")
        self.assertEqual(lost, ["ada", "lovelace"])

    def test_a_page_number_on_its_own_line_may_go(self):
        lost, invented = importer.verify("body\nPage 2 of 5\n", "body\n")
        self.assertEqual((lost, invented), ([], []))


class Converting(InAScratchHome):
    def _model_returns(self, markdown):
        directory = self.home / ".scout"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "fake-structured.md").write_text(markdown, encoding="utf-8")

    def test_a_clean_conversion_comes_back(self):
        self._model_returns(
            "# Ada Lovelace\n\n## Skills\n\n- Python, Postgres\n\n"
            "### Wilding Labs — Engineer\n\n2021\n"
        )
        converted = importer.convert(RESUME, FakeProvider())
        self.assertIn("### Wilding Labs", converted)

    def test_a_conversion_that_changed_a_word_is_refused(self):
        self._model_returns(RESUME.replace("Postgres", "Kubernetes"))
        with self.assertRaises(ScoutError) as caught:
            importer.convert(RESUME, FakeProvider())
        self.assertIn("dropped", str(caught.exception))
        self.assertIn("added", str(caught.exception))

    def test_a_model_that_returns_nothing(self):
        self._model_returns("   ")
        with self.assertRaises(ScoutError) as caught:
            importer.convert(RESUME, FakeProvider())
        self.assertIn("returned nothing", str(caught.exception))


class Reading(InAScratchHome):
    def test_a_file_that_is_not_there(self):
        with self.assertRaises(ScoutError) as caught:
            importer.read(self.home / "nowhere.pdf")
        self.assertIn("no file at", str(caught.exception))

    def test_a_pdf_that_is_a_scan_has_no_text_in_it(self):
        path = self.home / "scan.pdf"
        path.write_text("not really a pdf", encoding="utf-8")
        reader = unittest.mock.Mock(pages=[unittest.mock.Mock(extract_text=lambda: "")])
        with (
            unittest.mock.patch("pypdf.PdfReader", return_value=reader),
            self.assertRaises(ScoutError) as caught,
        ):
            importer.read(path)
        self.assertIn("No text could be read", str(caught.exception))

    def test_a_pdf_with_text_in_it(self):
        path = self.home / "resume.pdf"
        path.write_text("not really a pdf", encoding="utf-8")
        page = unittest.mock.Mock(extract_text=lambda: "Ada Lovelace\x00")
        with unittest.mock.patch(
            "pypdf.PdfReader", return_value=unittest.mock.Mock(pages=[page])
        ):
            self.assertEqual(importer.read(path), "Ada Lovelace")

    def test_a_text_file_is_read_as_it_is(self):
        path = self.home / "resume.txt"
        path.write_text(RESUME, encoding="utf-8")
        self.assertEqual(importer.read(path), RESUME)


class Employers(unittest.TestCase):
    def test_it_names_what_became_a_heading(self):
        markdown = "### Wilding Labs — Engineer\n### Thornfield Systems\n"
        self.assertEqual(
            importer.employers(markdown), ["Wilding Labs", "Thornfield Systems"]
        )
