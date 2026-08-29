"""Getting a real resume in.

scout reads `resumes/master.md`, and nobody has a markdown resume. Somebody
converting four pages by hand before they can try the tool will not try it.

**The model reads the structure and a deterministic check proves it changed
nothing.** That split is the point. Recognising which line is an employer and
which is a bullet is what a model is genuinely better at than a rule: resume
formats vary without limit, and a parser chasing them gets more fragile with
every one it learns — the first version of this file was a pile of regular
expressions, and teaching it two employers it had missed silently lost it
seven it had been finding.

What a model cannot be trusted with is the content, because the master resume
is the document every other check is made against. An importer that dropped a
job or reworded a bullet would poison the one source of truth scout has, and
every check downstream would agree with it, because it would be checking
against the damage.

So `verify` requires **word conservation in both directions**: every word of
the original must appear in the output, and every word of the output must
have been in the original. The model may add markdown markers and whitespace
and nothing else. That is a tighter guarantee than tailoring's — there the
model is meant to rewrite, so only new *names* can be caught; here nothing may
change at all, so everything can be.
"""

import re
from pathlib import Path

from .errors import ScoutError
from .providers import Provider

# A page number on its own line.
PAGE_NUMBER = re.compile(r"^\s*(page\s*)?\d{1,3}\s*(of\s*\d{1,3})?\s*$", re.IGNORECASE)

# How many times a line has to repeat before it is page furniture rather than
# content. A running header carrying somebody's name appears on every page, so
# insisting the output keep all six copies would refuse every real PDF.
REPEATS_BEFORE_FURNITURE = 3

WORD = re.compile(r"[A-Za-z0-9+#/.&']+")

# `#`, `##`, `###`, `-` — markdown, not words. They are only excluded when
# that is all the token is, because `C#` and `.NET` are things people put on
# resumes.
MARKER = re.compile(r"^[#*_>-]+$")


def read(path: Path) -> str:
    """The text of a resume, whatever it arrived as."""
    if not path.exists():
        raise ScoutError(
            f"There is no file at {path}.",
            detail="Pass the path to your resume: scout import ~/resume.pdf",
        )
    if path.suffix.lower() == ".pdf":
        return _from_pdf(path)
    return path.read_text(encoding="utf-8", errors="replace")


def _from_pdf(path: Path) -> str:
    import pypdf

    reader = pypdf.PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    text = text.replace("\x00", "")
    if not text.strip():
        raise ScoutError(
            f"No text could be read out of {path}.",
            detail=(
                "A PDF that is a scan of a page holds an image, not text. "
                "Export it again from whatever made it, or paste the text "
                "into a .txt file and import that."
            ),
        )
    return text


def _furniture(lines: list[str]) -> set[str]:
    """The lines a PDF repeats on every page, which the model may drop."""
    seen: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if stripped:
            seen[stripped] = seen.get(stripped, 0) + 1
    return {line for line, n in seen.items() if n >= REPEATS_BEFORE_FURNITURE}


def _words(text: str, *, source: bool = False) -> list[str]:
    lines = text.splitlines()
    if source:
        # Only the original is stripped of furniture. The output has no
        # furniture to strip, and would be the wrong place to guess at it.
        #
        # The *first* occurrence is kept. A resume whose running header is the
        # person's name has that name at the top of page one as content and on
        # every page after as furniture; dropping all of them would make the
        # name read as something the importer invented.
        furniture = _furniture(lines)
        kept: set[str] = set()
        keeping = []
        for line in lines:
            stripped = line.strip()
            if PAGE_NUMBER.match(line):
                continue
            if stripped in furniture:
                if stripped in kept:
                    continue
                kept.add(stripped)
            keeping.append(line)
        lines = keeping
    return [
        word.lower()
        for line in lines
        for word in WORD.findall(line)
        if not MARKER.match(word)
    ]


def verify(original: str, converted: str) -> tuple[list[str], list[str]]:
    """What the conversion lost, and what it invented.

    Both empty means the output holds exactly the words of the input, in some
    order, with markdown around them — which is the whole of what an importer
    is allowed to do.
    """
    before: dict[str, int] = {}
    for word in _words(original, source=True):
        before[word] = before.get(word, 0) + 1

    after: dict[str, int] = {}
    for word in _words(converted):
        after[word] = after.get(word, 0) + 1

    lost = [word for word, n in before.items() if after.get(word, 0) < n]
    invented = [word for word, n in after.items() if before.get(word, 0) < n]
    return sorted(lost), sorted(invented)


def convert(text: str, provider: Provider) -> str:
    """Ask for the same resume with markdown around it, and insist on it."""
    markdown = provider.structure(resume=text).strip()
    if not markdown:
        raise ScoutError("The model returned nothing to import.")

    lost, invented = verify(text, markdown)
    if lost or invented:
        raise ScoutError(
            _refusal(lost, invented),
            detail=(
                "Nothing was written. An importer may add markdown and "
                "nothing else: the master resume is what every other check is "
                "made against, so a word changed here is a wrong answer "
                "everywhere else. Try again, or import a .txt of your resume "
                "and structure it by hand."
            ),
        )
    return markdown + "\n"


def _refusal(lost: list[str], invented: list[str]) -> str:
    parts = []
    if lost:
        parts.append(f"dropped {len(lost)} word(s): " + " ".join(lost[:10]))
    if invented:
        parts.append(f"added {len(invented)} word(s): " + " ".join(invented[:10]))
    return "Refused the import: it " + ", and ".join(parts) + "."


def employers(markdown: str) -> list[str]:
    """The `###` headings, for saying what the import recognised."""
    return [
        re.split(r"\s+[—–-]\s+", line[4:].strip(), maxsplit=1)[0].strip()
        for line in markdown.splitlines()
        if line.startswith("### ")
    ]
