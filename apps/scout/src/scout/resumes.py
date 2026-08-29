"""The resume files on disk.

Resumes are files rather than rows because they are documents somebody opens,
edits, prints and attaches to an email. Putting them in the database would
mean a tool to get them back out again.
"""

from pathlib import Path

from . import paths
from .errors import ScoutError


def read_master() -> str:
    """The master resume, or a refusal that says where it looked."""
    path = paths.master_resume_path()
    if not path.exists():
        raise ScoutError(
            f"There is no master resume at {path}.",
            detail=(
                "Run `scout init` to write an example one there, then "
                "replace it with yours."
            ),
        )
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ScoutError(
            f"The master resume at {path} has nothing in it.",
            detail="Tailoring can only reorder what is already there.",
        )
    return text


def tailored_dir(ref: str) -> Path:
    return paths.resumes_dir() / ref


def write(ref: str, version: int, markdown: str) -> Path:
    """Write version ``version`` for ``ref`` and return where it went.

    Versions accumulate rather than overwrite, because the second attempt is
    usually not better than the first and the first is gone by the time
    anybody notices.
    """
    directory = tailored_dir(ref)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"v{version}.md"
    path.write_text(markdown, encoding="utf-8")
    return path
