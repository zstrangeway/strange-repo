"""What tailoring actually did to the master resume.

This is scout's own reading of the two documents, not the model's account of
itself — a model asked what it changed will tell you what it meant to change.
Diffing the files says what is there.

It matters more than it looks. The grounding check catches invention and not
inflation, so a number that grew or a "familiar with" that became an "expert
in" reaches the disk. This summary is where a person sees that before they
send it, which is the only defence against it there is.
"""

import difflib
import re
from dataclasses import dataclass, field

HEADING = re.compile(r"^(#{2,3})\s+(.*)$")


@dataclass
class Section:
    heading: str
    level: int
    body: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.heading.strip().lower()


def sections(markdown: str) -> list[Section]:
    """Split a resume into its `##` and `###` blocks, in order."""
    found: list[Section] = [Section(heading="", level=0)]
    for line in markdown.splitlines():
        match = HEADING.match(line)
        if match:
            found.append(Section(heading=match.group(2), level=len(match.group(1))))
        else:
            found[-1].body.append(line)
    # The preamble only counts if somebody wrote something above the first
    # heading; an empty one would report as a section that vanished.
    return [s for s in found if s.heading or any(line.strip() for line in s.body)]


@dataclass(frozen=True)
class Summary:
    """Every change, in the order somebody would want to read them."""

    moved_up: list[str]
    moved_down: list[str]
    dropped: list[str]
    added: list[str]
    rewritten: list[tuple[str, str]]

    def render(self) -> str:
        lines: list[str] = []
        for heading in self.moved_up:
            lines.append(f"  moved up      {heading}")
        for heading in self.moved_down:
            lines.append(f"  played down   {heading}")
        for heading in self.dropped:
            lines.append(f"  left out      {heading}")
        for heading in self.added:
            lines.append(f"  new section   {heading}")
        for before, after in self.rewritten:
            lines.append(f"  rewritten     {before}")
            lines.append(f"             -> {after}")
        if not lines:
            # Never empty. A blank summary reads like the summary failed
            # rather than like the draft came back unchanged.
            return "  nothing changed — the draft matches the master resume."
        return "\n".join(lines)


def compute(master: str, draft: str, *, rewrites: int = 12) -> Summary:
    """Diff the master against the draft, section by section."""
    before = sections(master)
    after = sections(draft)
    before_order = {s.key: i for i, s in enumerate(before)}
    after_order = {s.key: i for i, s in enumerate(after)}

    moved_up, moved_down = [], []
    for section in after:
        if section.key in before_order:
            # Compared as a position among the sections that survived, so
            # dropping one section does not report every later one as moved.
            was = sum(
                1
                for k in before_order
                if before_order[k] < before_order[section.key] and k in after_order
            )
            now = sum(
                1
                for k in after_order
                if after_order[k] < after_order[section.key] and k in before_order
            )
            if now < was:
                moved_up.append(section.heading)
            elif now > was:
                moved_down.append(section.heading)

    dropped = [s.heading for s in before if s.key not in after_order and s.heading]
    added = [s.heading for s in after if s.key not in before_order and s.heading]

    rewritten = _rewritten(master, draft, limit=rewrites)
    return Summary(moved_up, moved_down, dropped, added, rewritten)


def _rewritten(master: str, draft: str, *, limit: int) -> list[tuple[str, str]]:
    """Lines that survived in changed words, paired before and after.

    Only replacements — a line that moved is reported as its section moving,
    and listing it again here would bury the rewrites that matter.
    """
    old = [line for line in master.splitlines() if line.strip()]
    new = [line for line in draft.splitlines() if line.strip()]
    pairs: list[tuple[str, str]] = []
    matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "replace":
            continue
        for before, after in zip(old[i1:i2], new[j1:j2], strict=False):
            pairs.append((before.strip(), after.strip()))
            if len(pairs) == limit:
                return pairs
    return pairs
