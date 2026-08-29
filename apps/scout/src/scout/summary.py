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
    cut: list[str]
    fresh: list[str]

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
        for line in self.cut:
            lines.append(f"  cut           {line}")
        for line in self.fresh:
            lines.append(f"  new line      {line}")
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

    rewritten, cut, fresh = _line_changes(master, draft, limit=rewrites)
    return Summary(moved_up, moved_down, dropped, added, rewritten, cut, fresh)


# Below this, two lines are different things rather than one edited into the
# other. Tuned by hand against real drafts: "led a team of 3" against "led a
# team of 12" sits near 0.95, and two unrelated bullets from the same resume
# land around 0.3.
SAME_LINE = 0.6


def _body_lines(markdown: str) -> list[str]:
    """Every line that is resume content.

    Headings are left out because a heading that moved is reported as its
    section moving, and reporting it twice buries the lines that matter.

    So are HTML comments. `scout init` writes the format rules into the master
    resume as one, a model quite reasonably drops it, and the first real smoke
    run then reported seven lines of scout's own instructions as content the
    draft had cut.
    """
    lines, in_comment = [], False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("<!--"):
            in_comment = True
        if in_comment:
            in_comment = "-->" not in stripped
            continue
        if stripped and not HEADING.match(line):
            lines.append(stripped)
    return lines


def _line_changes(
    master: str, draft: str, *, limit: int
) -> tuple[list[tuple[str, str]], list[str], list[str]]:
    """What happened to the prose: rewritten, cut, and newly written.

    Deliberately not `difflib.get_opcodes` over the two documents. That
    aligns by position, so a bullet the model deleted and an unrelated one it
    promoted to the same spot come back as a `replace` — and get reported as
    a rewrite of one into the other. A real draft did exactly that on the
    first run against a real model, and the summary said a line had been
    reworded when it had actually been thrown away. Since this summary is the
    only thing standing between somebody and a claim the grounding check
    cannot catch, it has to describe what happened rather than what lines up.

    So: a line is gone only if it is nowhere in the draft, new only if it is
    nowhere in the master, and a rewrite only when a gone line and a new line
    genuinely resemble each other.
    """
    before, after = _body_lines(master), _body_lines(draft)
    gone = [line for line in before if line not in after]
    fresh = [line for line in after if line not in before]

    rewritten: list[tuple[str, str]] = []
    for old in list(gone):
        match = max(
            fresh,
            key=lambda new: difflib.SequenceMatcher(a=old, b=new).ratio(),
            default=None,
        )
        if match is None:
            break
        if difflib.SequenceMatcher(a=old, b=match).ratio() >= SAME_LINE:
            rewritten.append((old, match))
            gone.remove(old)
            fresh.remove(match)

    return rewritten[:limit], gone[:limit], fresh[:limit]
