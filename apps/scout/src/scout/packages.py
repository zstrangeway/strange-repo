"""What is about to be sent, and whether somebody said yes to it.

The step the flow turns on, and the easiest one to build badly. If approving
means reading a four-page resume every time, tailoring saved nobody anything —
writing was swapped for proofreading. If it means glancing and clicking yes,
the approval is theatre and whatever the model invented goes out under
somebody's name.

Two ideas hold this together.

**Approval scope and check scope are different, and only one of them is
hard.** `grounding.py` can speak to a tailored resume, because that is a
projection of the master resume and "did anything new appear" is a well-formed
question about it. It cannot speak to "why do you want to work here" — genuine
composition, which it would be wrong to refuse. That does not have to be
solved to be safe: show everything, check what can be checked, and say which
was which. The failure this exists to prevent is not unchecked text; it is
unchecked text presented as though something had checked it.

**Approval is of particular words, not of a posting.** It is stored as a
snapshot and compared by fingerprint, so re-tailoring or editing an answer
withdraws it. A flag would still read "approved" after something regenerated
the resume underneath it, and nobody would ever find out.

⚠️ scout does not submit anything. The browser belongs to whatever agent is
driving — it has the user's own logged-in sessions — and scout has no business
growing a second one. scout's job ends at an approved package.
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from . import postings
from .errors import ScoutError

# What the deterministic check cannot speak to, said in the artifact itself
# rather than only in a README nobody reads at approval time.
UNCHECKED_MEANS = (
    "Text scout did not write is not checked against the master resume: "
    "an answer about why you want the job is composition, not a projection "
    "of anything, and there is nothing to check it against. Read it."
)


@dataclass(frozen=True)
class Item:
    """One thing that is going to be submitted.

    ``label`` is the item's identity and ``detail`` is display only. They are
    separate because the resume's version belongs on screen but not in the
    identity: with the version in the label, tailoring again reads as one item
    vanishing and another appearing, and the package reports "Resume version
    2, Resume version 1 changed" instead of "the resume changed".
    """

    kind: str  # resume | answer
    label: str
    body: str
    checked: bool
    note: str | None = None
    detail: str | None = None

    @property
    def heading(self) -> str:
        return f"{self.label}, {self.detail}" if self.detail else self.label

    def fingerprint(self) -> list[str]:
        return [self.kind, self.label, self.body]


@dataclass(frozen=True)
class Package:
    posting: postings.Posting
    items: list[Item]
    approved_at: str | None
    approved_snapshot: list[Item]

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.items)

    @property
    def approved(self) -> bool:
        """Whether these exact words were the ones somebody said yes to."""
        return (
            self.approved_at is not None
            and _fingerprint(self.approved_snapshot) == self.fingerprint
        )

    @property
    def changed_since_approval(self) -> list[str]:
        """What is different from what was approved, by label."""
        if self.approved_at is None:
            return []
        was = {(item.kind, item.label): item.body for item in self.approved_snapshot}
        now = {(item.kind, item.label): item.body for item in self.items}
        changed = [
            label for (_, label), body in now.items() if was.get((_, label)) != body
        ]
        gone = [label for (_, label) in was if (_, label) not in now]
        return changed + gone

    @property
    def fully_checked(self) -> bool:
        return all(item.checked for item in self.items)

    def render(self) -> str:
        lines = [f"Package for {self.posting.ref}", ""]
        for item in self.items:
            mark = "checked" if item.checked else "NOT CHECKED"
            lines.append(f"--- {item.heading}  [{mark}]")
            if item.note:
                lines.append(item.note)
            lines.append("")
            lines.append(item.body.strip())
            lines.append("")

        if self.fully_checked:
            lines.append(
                "Everything in this package was checked against the master "
                "resume: nothing in it names an employer, job title, skill or "
                "date the master does not."
            )
        else:
            # Said plainly, every time. A package that reads as a clean bill of
            # health for text nothing examined converts somebody's caution into
            # confidence, and is wrong to.
            unchecked = [item.heading for item in self.items if not item.checked]
            lines.append(
                "NOT everything in this package was checked. Checked against "
                "the master resume: "
                + ", ".join(item.heading for item in self.items if item.checked)
                + ". Not checked: "
                + ", ".join(unchecked)
                + "."
            )
            lines.append(UNCHECKED_MEANS)

        lines.append("")
        if self.approved:
            lines.append(f"Approved {self.approved_at}.")
        elif self.approved_at is not None:
            lines.append(
                f"NOT approved. It was approved {self.approved_at}, and then "
                + ", ".join(self.changed_since_approval)
                + " changed. Approving is of particular words, so it has to be "
                "approved again."
            )
        else:
            lines.append("Not approved yet.")
        return "\n".join(lines)


def _fingerprint(items: list[Item]) -> str:
    payload = json.dumps([item.fingerprint() for item in items], sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _latest_resume(connection: sqlite3.Connection, posting_id: int):
    return connection.execute(
        "SELECT version, path, summary FROM resumes WHERE posting_id = ?"
        " ORDER BY version DESC LIMIT 1",
        (posting_id,),
    ).fetchone()


def assemble(connection: sqlite3.Connection, ref: str) -> Package:
    """Start a package for ``ref``, or return the one already there."""
    posting = postings.read(connection, ref)
    if _latest_resume(connection, posting.id) is None:
        raise ScoutError(
            f"There is no tailored resume for {ref} yet.",
            detail=f"Tailor one first: scout tailor {ref}",
        )
    if _row(connection, posting.id) is None:
        connection.execute(
            "INSERT INTO packages (posting_id, created_at) VALUES (?, ?)",
            (posting.id, _now()),
        )
    return read(connection, ref)


def _row(connection: sqlite3.Connection, posting_id: int):
    return connection.execute(
        "SELECT * FROM packages WHERE posting_id = ?", (posting_id,)
    ).fetchone()


def read(connection: sqlite3.Connection, ref: str) -> Package:
    posting = postings.read(connection, ref)
    row = _row(connection, posting.id)
    if row is None:
        raise ScoutError(
            f"There is no package for {ref} yet.",
            detail=f"Assemble one: scout package {ref}",
        )

    items: list[Item] = []
    resume = _latest_resume(connection, posting.id)
    items.append(
        Item(
            kind="resume",
            label="Resume",
            detail=f"version {resume['version']}",
            # Read from disk rather than from the row: the file is what would
            # actually be attached, and if somebody edited it by hand that is
            # what they are approving.
            body=Path(resume["path"]).read_text(encoding="utf-8"),
            checked=True,
            note=resume["summary"],
        )
    )
    for answer in connection.execute(
        "SELECT question, body FROM answers WHERE package_id = ? ORDER BY id",
        (row["id"],),
    ).fetchall():
        items.append(
            Item(
                kind="answer",
                label=answer["question"],
                body=answer["body"],
                checked=False,
            )
        )

    snapshot = [Item(**item) for item in json.loads(row["approved_snapshot"] or "[]")]
    return Package(posting, items, row["approved_at"], snapshot)


def add_answer(
    connection: sqlite3.Connection, ref: str, question: str, body: str
) -> Package:
    """Put text headed for the form into the package.

    Replaces an answer to the same question rather than accumulating two, so
    that a session correcting itself does not submit both.
    """
    if not body.strip():
        raise ScoutError(
            "That answer was empty.",
            detail="Nothing was added. An empty box is not an answer.",
        )
    package = assemble(connection, ref)
    row = _row(connection, package.posting.id)
    connection.execute(
        "INSERT INTO answers (package_id, question, body, created_at)"
        " VALUES (?, ?, ?, ?)"
        " ON CONFLICT (package_id, question) DO UPDATE SET body = excluded.body",
        (row["id"], question.strip(), body.strip(), _now()),
    )
    return read(connection, ref)


def approve(connection: sqlite3.Connection, ref: str) -> Package:
    """Record that somebody said yes to these exact words."""
    package = read(connection, ref)
    connection.execute(
        "UPDATE packages SET approved_at = ?, approved_snapshot = ?"
        " WHERE posting_id = ?",
        (
            _now(),
            json.dumps([item.__dict__ for item in package.items]),
            package.posting.id,
        ),
    )
    return read(connection, ref)
