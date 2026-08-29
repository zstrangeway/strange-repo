"""Tailoring a resume to one posting.

The order here is the feature: ask the model, check what came back, and only
then write. Nothing reaches the disk until the grounding check has passed,
which is what makes "refused" mean the file is not there rather than there
and wrong.
"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from . import grounding, postings, resumes, summary
from .errors import ScoutError
from .providers import Provider


@dataclass(frozen=True)
class Tailored:
    posting: postings.Posting
    version: int
    path: Path
    summary: summary.Summary

    def render(self) -> str:
        return f"Wrote {self.path}\n\nWhat changed:\n" + self.summary.render()


def _next_version(connection: sqlite3.Connection, posting_id: int) -> int:
    row = connection.execute(
        "SELECT MAX(version) AS latest FROM resumes WHERE posting_id = ?",
        (posting_id,),
    ).fetchone()
    return (row["latest"] or 0) + 1


def tailor(connection: sqlite3.Connection, ref: str, provider: Provider) -> Tailored:
    """Tailor the master resume for ``ref``.

    Raises ``ScoutError`` — having written nothing — if the draft claims
    anything the master resume does not.
    """
    posting = postings.read(connection, ref)
    master = resumes.read_master()

    draft = provider.tailor(master=master, posting=posting.body)

    findings = grounding.check(master, draft)
    if findings:
        raise ScoutError(
            _refusal(findings),
            detail=(
                "Nothing was written. The draft is below — tailor again to "
                "ask for another one.\n\n" + draft
            ),
        )

    version = _next_version(connection, posting.id)
    path = resumes.write(posting.ref, version, draft)
    connection.execute(
        "INSERT INTO resumes (posting_id, version, path, summary, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (
            posting.id,
            version,
            str(path),
            summary.compute(master, draft).render(),
            datetime.now(UTC).isoformat(timespec="seconds"),
        ),
    )
    return Tailored(posting, version, path, summary.compute(master, draft))


def _refusal(findings: list[grounding.Finding]) -> str:
    """One sentence naming what the draft claimed.

    Every finding is named rather than only the first: sending somebody back
    around the loop once per invented word is how a tool gets abandoned.
    """
    if len(findings) == 1:
        return f"Refused the draft: {findings[0]}."
    listed = ", ".join(f'"{finding.term}"' for finding in findings)
    return f"Refused the draft: {listed} are not in the master resume."
