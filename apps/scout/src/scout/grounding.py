"""The check that a tailored resume invented nothing.

Tailoring may reorder, reweight and rephrase what the master resume already
says, and may not add to it. This module is what holds that line, and it is
deliberately not the prompt: a prompt is a request, and this is the part that
still works when the model ignores it. It is also the only kind of check this
repo can gate CI on, since a check that is itself a model call cannot be
tested without calling a model.

⚠️ It catches invention, not inflation. A name that is not in the master is
caught every time. "Led a team of 3" becoming "led a team of 12", or
"familiar with Terraform" becoming "expert in Terraform", is not caught here
and is not caught by anything cheap. That is why the summary of what changed
is not a nicety — see `summary.py`. The check is a floor that fails closed;
the summary is where a person catches the rest.

Three things are compared, in descending order of confidence:

1. **Employers and job titles**, from `###` headings. Exact, because the
   master's own structure says what they are.
2. **Skills**, from the `## Skills` section of each document.
3. **Dates, against the employer they sit under.** A year the master does not
   give that employer is refused. This one was added after the first real
   smoke run, where a model handed the second employer the first one's dates
   — a resume claiming four years somewhere nobody worked, which is invented
   experience however narrowly you read the word.
4. **Proper nouns in prose** — a capitalised word mid-sentence, or anything in
   `KNOWN_TECHNOLOGIES` at any case, that the master never mentions.
"""

import re
from dataclasses import dataclass

# Technologies common enough to be worth catching even in lower case, which
# the capitalisation sweep below would otherwise walk straight past. Not a
# complete list of anything and not meant to be — it is the difference between
# catching "expert in kubernetes" and not.
KNOWN_TECHNOLOGIES = frozenset(
    """
    ansible apollo argocd athena aurora aws azure bash bigquery cassandra
    celery chef circleci clickhouse clojure cobol cypress dagger dart datadog
    dbt django docker dotnet dynamodb elasticsearch elixir ember erlang fargate
    fastapi firebase flask flink flutter gcp gitlab go golang grafana graphql
    grpc hadoop haskell hbase helm hibernate ibm istio jenkins jira jquery
    julia kafka keras kotlin kubernetes lambda langchain laravel linux lua
    matlab memcached mongodb mysql neo4j nestjs netlify nextjs nginx nodejs
    numpy nuxt oauth opensearch openshift opentelemetry oracle pandas perl
    php playwright postgres postgresql prometheus puppet pulumi pytest python
    pytorch rabbitmq rails react redis redshift redux ruby rust salesforce
    scala selenium sentry snowflake solidity spark splunk spring sqlalchemy
    sqlite storybook stripe supabase svelte swift tableau tensorflow terraform
    typescript vercel vue vuejs webpack websockets zookeeper
    """.split()
)

# The gap between an employer and a job title in a heading.
HEADING_SPLIT = re.compile(r"\s+[—–-]\s+")

# A bullet or list marker at the head of a line.
BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")

# Any four-digit year. Compared as a set per employer rather than as a string,
# so an en dash against a hyphen, or "2021-2025" against "2021 – 2025", is the
# same claim — which it is.
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")

# Kept because a resume writes them and they are never a claim about anybody.
MONTHS = frozenset(
    """
    january february march april may june july august september october
    november december jan feb mar apr jun jul aug sep sept oct nov dec
    monday tuesday wednesday thursday friday present current today
    """.split()
)


@dataclass(frozen=True)
class Finding:
    """Something in the draft that the master resume does not support."""

    kind: str  # employer | title | skill | term | date
    term: str
    # Only dates carry one: a year is not wrong on its own, only wrong under
    # a particular employer.
    employer: str | None = None

    def __str__(self) -> str:
        if self.employer is not None:
            return (
                f'"{self.term}" is not a date the master resume gives for '
                f'"{self.employer}"'
            )
        return f'"{self.term}" is not in the master resume'


def normalise(text: str) -> str:
    """Lower case, and no punctuation hanging off either end.

    "Postgres" and "postgres." at the end of a sentence are the same claim,
    and a check that refuses one of them trains somebody to stop reading its
    refusals. `+` and `#` survive, because C++ and C# are skills.
    """
    return text.lower().strip(".,;:!?()[]{}<>\"'`*_ \t")


def _words(text: str) -> set[str]:
    return {normalise(token) for token in re.split(r"\s+", text) if normalise(token)}


def headings(markdown: str) -> list[tuple[str, str | None]]:
    """Every `###` heading, split into employer and job title."""
    found = []
    for line in markdown.splitlines():
        if line.startswith("### "):
            parts = HEADING_SPLIT.split(line[4:].strip(), maxsplit=1)
            found.append(
                (parts[0].strip(), parts[1].strip() if len(parts) > 1 else None)
            )
    return found


def skills(markdown: str) -> list[str]:
    """The entries under a `## Skills` heading.

    Commas, bullets and newlines all separate, because people write that
    section every one of those ways.
    """
    section: list[str] = []
    collecting = False
    for line in markdown.splitlines():
        if line.startswith("## "):
            collecting = line[3:].strip().lower().startswith("skill")
            continue
        if collecting:
            section.append(line)
    entries = re.split(r"[,\n•|]|^\s*[-*]\s+", "\n".join(section), flags=re.MULTILINE)
    return [entry.strip() for entry in entries if entry.strip()]


def years_by_employer(markdown: str) -> dict[str, set[str]]:
    """Every year that appears under each `###` employer heading.

    Sectioned by heading rather than read as a whole document, because the
    mistake being caught is a date under the *wrong* employer — and every year
    in it is a year the master mentions somewhere.
    """
    found: dict[str, set[str]] = {}
    current: str | None = None
    for line in markdown.splitlines():
        if line.startswith("### "):
            current = normalise(HEADING_SPLIT.split(line[4:].strip(), maxsplit=1)[0])
            found.setdefault(current, set())
        elif line.startswith("## "):
            current = None
        elif current is not None:
            found[current].update(YEAR.findall(line))
    return found


@dataclass(frozen=True)
class Master:
    """What the master resume actually says, as sets to check against."""

    employers: frozenset[str]
    titles: frozenset[str]
    skills: frozenset[str]
    words: frozenset[str]

    @classmethod
    def parse(cls, markdown: str) -> "Master":
        employers, titles = set(), set()
        for employer, title in headings(markdown):
            employers.add(normalise(employer))
            if title:
                titles.add(normalise(title))
        return cls(
            employers=frozenset(employers),
            titles=frozenset(titles),
            skills=frozenset(normalise(skill) for skill in skills(markdown)),
            words=frozenset(_words(markdown)),
        )

    def mentions(self, term: str) -> bool:
        """Whether the master says this anywhere at all.

        Every word of a multi-word term has to appear, which is what lets
        "Wilding Labs" match a master that writes it as part of a longer
        heading, while "Initech Systems" still fails on "initech".
        """
        return all(word in self.words for word in _words(term))


def _prose_findings(master: Master, draft: str) -> list[Finding]:
    """Proper nouns and known technologies the master never mentions.

    The first word of a line or a sentence is skipped: it is capitalised
    because of where it sits, not because it names anything.
    """
    findings, seen = [], set()
    for line in draft.splitlines():
        if line.startswith("#"):
            continue  # headings are checked exactly, above
        # The marker is not the first word. Without stripping it, "- Ran the
        # migration" checks "Ran" as though it were mid-sentence, and every
        # rephrased bullet reports a false invention.
        tokens = re.split(r"\s+", BULLET.sub("", line.strip()))
        starts_sentence = True
        for token in tokens:
            word = normalise(token)
            candidate = (
                word
                and len(word) > 1
                and word not in MONTHS
                and not word.replace("+", "").replace("#", "").isdigit()
                and (
                    (token[:1].isupper() and not starts_sentence)
                    or word in KNOWN_TECHNOLOGIES
                )
            )
            if candidate and word not in seen and word not in master.words:
                seen.add(word)
                findings.append(Finding("term", token.strip(".,;:")))
            starts_sentence = token.endswith((".", "!", "?", ":"))
    return findings


def check(master_markdown: str, draft: str) -> list[Finding]:
    """Everything in ``draft`` that ``master_markdown`` does not support.

    An empty list means the draft only reordered, reweighted or rephrased.
    """
    master = Master.parse(master_markdown)
    findings: list[Finding] = []

    for employer, title in headings(draft):
        if not master.mentions(employer):
            findings.append(Finding("employer", employer))
        if title and normalise(title) not in master.titles:
            findings.append(Finding("title", title))

    for skill in skills(draft):
        if not master.mentions(skill):
            findings.append(Finding("skill", skill))

    theirs = years_by_employer(master_markdown)
    # Headings are matched normalised and reported as written, so the refusal
    # names the employer the way the resume does.
    as_written = {normalise(employer): employer for employer, _ in headings(draft)}
    for employer, years in years_by_employer(draft).items():
        # An employer that is not in the master at all is already reported
        # above; saying its dates are wrong too is noise on top of that.
        if employer not in theirs:
            continue
        for year in sorted(years - theirs[employer]):
            findings.append(
                Finding("date", year, employer=as_written.get(employer, employer))
            )

    known = {finding.term.lower() for finding in findings}
    findings.extend(
        finding
        for finding in _prose_findings(master, draft)
        if finding.term.lower() not in known
    )
    return findings
