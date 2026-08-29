"""What the documents claim, checked against what the code does.

Prose cannot be type-checked and this does not try. It checks the two shapes
that are exact — a named event kind and a named tool — and leaves the rest of
the English alone.

Both directions matter, and they catch opposite mistakes:

* A document naming an event kind that does not exist is **stale by removal**:
  something was renamed and the prose kept the old word. Found one the day
  this was written — gary-api's README documented the party-moved event under
  the bare name it had before adversaries landed.

  A document quoting a wrong kind trips this too, because the pattern reads a
  shape and not an intent. That is a fair price and the fix is to describe the
  old name rather than spell it in the shape that means a claim; an allowlist
  would only ever be used, eventually, to silence a real hit.

* A document that does not name a tool gary has is **stale by addition**, and
  this is the one that actually bit. gary-api's README said there was no
  combat, thirty lines below the section describing combat, because
  ``begin_combat`` landed and nothing made the prose account for it. A scan
  for names that no longer exist could never have caught that: the wrong
  sentence named nothing at all.

Deliberately crude, like ``test_pluggable.py``, and for the same reason: a
check nobody can explain is a check somebody deletes.
"""

import pathlib
import re
import unittest

from gary_api import narration, world

REPO = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parents[1] / "README.md"

# ``"kind": "party-moved"``, in any document, however it is spaced. Narrow on
# purpose: the bare word "moved" is English and appears everywhere, so only
# the position that means an event kind is read as one.
NAMES_A_KIND = re.compile(r'"kind"\s*:\s*"([a-z-]+)"')


def documents() -> list[pathlib.Path]:
    """Every markdown file that is ours."""
    return [
        path
        for path in sorted(REPO.rglob("*.md"))
        if not any(
            part in {".venv", "node_modules", ".pytest_cache", ".next"}
            for part in path.parts
        )
    ]


class DocumentsTests(unittest.TestCase):
    def test_no_document_names_an_event_kind_that_does_not_exist(self):
        offences = []
        for path in documents():
            for number, line in enumerate(path.read_text().splitlines(), start=1):
                for named in NAMES_A_KIND.findall(line):
                    if named not in world.KINDS:
                        offences.append(
                            f"{path.relative_to(REPO)}:{number} says "
                            f"{named!r}, which is not an event kind"
                        )

        self.assertEqual(
            offences,
            [],
            "these name a kind the world does not have:\n" + "\n".join(offences),
        )

    def test_the_readme_names_every_tool_gary_is_offered(self):
        """The check that would have caught "there is no combat".

        A tool that lands without the prose accounting for it fails here, on
        the commit that adds it, rather than months later when somebody reads
        the file and notices it describing a different app.
        """
        text = HERE.read_text()
        missing = [name for name in narration.TOOLS if f"`{name}`" not in text]

        self.assertEqual(
            missing,
            [],
            "gary-api's README does not mention these tools:\n"
            + "\n".join(f"  {name}" for name in missing),
        )

    def test_the_checks_can_actually_fail(self):
        # A check that cannot fail is worse than no check — and this one reads
        # files by glob, which is exactly the sort of thing that quietly
        # matches nothing after a directory moves.
        found = documents()
        self.assertTrue(found, "the scan found no documents at all")
        self.assertIn("BACKLOG.md", [path.name for path in found])
        self.assertIn("README.md", [path.name for path in found])
        self.assertTrue(HERE.exists())

        # And that the kind pattern reads what it claims to.
        self.assertEqual(
            NAMES_A_KIND.findall('event: world data: {"kind": "party-moved"}'),
            ["party-moved"],
        )


if __name__ == "__main__":
    unittest.main()
