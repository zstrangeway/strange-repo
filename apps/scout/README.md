# scout

A job search assistant that runs on your machine, against your own model key.

Save a posting, tailor your resume to it, and log where the application got
to. Three things, a CLI and an MCP server, and nothing else — no dashboard, no
account, no Kanban board, and nothing that applies to a job on your behalf.

**Everything stays here.** Postings and application history are rows in a
SQLite file under the directory you run it in; resumes are markdown files
beside them. The only thing that ever leaves the machine is one API call, made
with your key, when you ask for a tailored resume. Saving a posting and
logging a status never call a model at all.

## Quickstart

From a fresh clone, this reaches a logged application in about two minutes.

```sh
cd apps/scout
uv sync                                  # once
export OPENROUTER_API_KEY=sk-or-...      # yours; scout never stores it

mkdir -p ~/job-search && cd ~/job-search
export SCOUT_HOME=$PWD                   # or just run scout from here

uv run --directory /absolute/path/to/apps/scout scout init
```

`init` writes `resumes/master.example.md` and `resumes/master.md`. Replace the
second with your own resume — keeping the two rules in the comment at the top
of it — and then:

```sh
scout save --url https://job-boards.greenhouse.io/acme/jobs/4012345
# or, for a board that blocks fetches:
pbpaste | scout save --text - --title "Staff Engineer" --company "Orrery"

scout list
scout tailor orrery-staff-engineer
scout log orrery-staff-engineer applied --note "referral from Ada"
scout show orrery-staff-engineer
```

That is the whole tool.

### Saving from a URL

Give it the **posting's own URL**, not the board's index. scout fetches the
page itself and keeps the readable part, dropping navigation and footers.

It refuses, loudly and without saving, when the page is not a posting:

| | |
| --- | --- |
| A board's index page | "That looks like a list of jobs rather than one posting" |
| A shell that fills itself in with JavaScript | "There was no readable posting in …" |
| A board that answers 403 | "The board refused the fetch" |

All three tell you to paste the text instead, which always works. Verified
against real boards: an individual Greenhouse posting saves cleanly, and both
Greenhouse's and python.org's index pages are refused.

## The one thing worth understanding

**Tailoring may reorder, reweight and rephrase your master resume. It may not
add to it.** A resume that claims Kubernetes because the posting asked for
Kubernetes is a lie told in your name, and you will not find out about it
until somebody asks you about it out loud.

So the model's draft is not trusted. Before anything is written, scout checks
every employer, job title and skill in the draft against your master resume,
and every date against the employer it sits under. A draft that introduces one
is refused whole — nothing partial reaches the disk — and scout tells you which
word it caught and shows you the draft it threw away.

That check is in scout, not in the prompt. The prompt asks; this is the part
that holds when the model ignores it.

### ⚠️ What the check does not do

It catches **invention**, not **inflation**.

| Caught | Not caught |
| --- | --- |
| An employer you never worked for | "led a team of 3" becoming "led a team of 12" |
| A skill you never claimed | "familiar with Terraform" becoming "expert in Terraform" |
| A job title you never held | "ran the upgrade" becoming "applied deep expertise to" |
| A year the master never gives that employer | |

The date row was not thought of — it was found. The first real smoke run
handed the second employer the first one's dates, and every year in the draft
appeared somewhere in the master, so nothing else caught it. That is four
years somewhere nobody worked.

The third row on the right was found the same way, on the same run: the
posting asked for "deep Postgres experience", and a bullet reading "ran the
Postgres upgrade" came back as "applied deep Postgres expertise to". No new
name, so the check passed it — and the summary showed it, which is the whole
argument for the summary.

Nothing cheap catches the right-hand column, and scout does not pretend to.
That is why every tailoring prints **what changed** — sections moved, lines
rewritten, before and after. Read it before you send the resume. It is the
only thing standing between you and the right-hand column.

### How it reads your master resume

Two rules, both in the comment at the top of the generated example:

- every employer is an `### Employer — Job title` heading
- every skill you claim is under `## Skills`

That structure is what lets the check say *"Initech is not in the master
resume"* rather than something vaguer.

## Approving what gets sent

scout does not submit anything, and is not going to — the browser belongs to
whatever agent is driving, and it has your logged-in sessions. What scout
owns is the step before: **a package**, which is everything about to be
submitted for one posting, and a record of whether you said yes to it.

```sh
scout package orrery-staff-engineer                   # everything, in full
scout answer orrery-staff-engineer "Why us?" "$(pbpaste)"
scout approve orrery-staff-engineer
```

Two rules make this worth having rather than a rubber stamp.

**A package shows everything; the check covers what it honestly can.** The
tailored resume is checked against your master. A cover letter is not, and
cannot be — "why do you want to work here" is composition, not a projection of
your resume, and there is nothing to check it against. So every item is marked
`[checked]` or `[NOT CHECKED]`, and a package containing anything unchecked
says so in words. The failure this exists to prevent is not unchecked text; it
is unchecked text presented as though something had verified it.

**Approval is of those exact words, not of that posting.** Re-tailoring the
resume, or changing or adding an answer, withdraws it — and the package then
says what changed and when it had been approved. Without that, "approved"
would be a flag that stayed true while something regenerated the resume
underneath it, and what got sent would not be what anybody agreed to.

## Statuses

```
saved → applied → screening → interview → offer
                                        ↘ rejected / ghosted
```

Forward one step at a time. `rejected` and `ghosted` are reachable from
anywhere, and are not a dead end — recruiters resurface, and logging
`screening` against a ghosted application is allowed and keeps the ghosting in
the history.

The path is enforced because of the mistake it catches: logging `offer`
against the wrong posting out of a list of thirty. scout refuses it and says
what you *can* log from where you are.

Nothing is ever overwritten. The status is the last entry in an append-only
log, so `scout show` can tell you when you applied and how long they sat on
it — which a status column throws away every time it is written.

## In Claude Code

Add this to `.mcp.json` in your project, or to `~/.claude.json`:

```json
{
  "mcpServers": {
    "scout": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/apps/scout", "scout-mcp"],
      "env": {
        "SCOUT_HOME": "/absolute/path/to/your/job-search",
        "OPENROUTER_API_KEY": "sk-or-..."
      }
    }
  }
}
```

That exposes eight tools. `save_posting`, `tailor_resume` and `log_status` are
the capabilities. `list_postings` and `edit_posting` are there because a
session that cannot see what it saved, or fill in a company scout would not
guess, sends you back to a terminal mid-flow. `get_package`, `add_answer` and
`approve_package` are the approval step — the one that makes "show it to me
before you send it" mean something.

The intended shape is that the agent finds the posting and drives the browser,
and scout supplies the constraint: a resume that cannot claim what you have
not done, and a package you actually saw before it went.

A refusal comes back as a failed tool result carrying the reason, not as an
exception — so when a draft invents an employer, the model reads *why* and can
tell you, rather than the turn dying.

> The block above is not decoration: `features/mcp.feature` reads this README,
> pulls that command out of it, and starts a server with it. If it drifts from
> what the package installs, the specs go red.

## Commands

| | |
| --- | --- |
| `scout init` | Create `resumes/` and an example master resume |
| `scout save --url URL` / `--text TEXT` | Save a posting (`--text -` reads stdin) |
| `scout list [--in-play]` | Everything saved, or only what has not ended |
| `scout show REF` | One posting, its history and its text |
| `scout edit REF --company X` | Fill in what scout would not guess |
| `scout tailor REF` | Tailor your resume for it, as a new version |
| `scout package REF` | Everything about to be submitted, and what was checked |
| `scout answer REF Q A` | Add form text to the package (`A` may be `-` for stdin) |
| `scout approve REF` | Say yes to the package exactly as it stands |
| `scout log REF STATUS [--note N]` | Move an application along |
| `scout note REF NOTE` | Add a note without changing the status |
| `scout mcp` | Run the MCP server on stdio |

`scout` never guesses a company. A wrong one is worse than a blank one: it is
the field you read back weeks later to remember who you wrote to.

## Model and cost

One provider — OpenRouter, with your key from `OPENROUTER_API_KEY`. The
default model is **`anthropic/claude-sonnet-5`**, and `SCOUT_MODEL` reaches
anything else it serves.

One provider is not one model. A direct Anthropic client was written and then
deleted: it was a second way to reach models the router already reaches, and
it could not do the one thing the router can — serve `:free` models, which is
what makes the smoke check below cost nothing.

The client is `openai`, even though a Claude is usually on the other end:
OpenRouter serves an OpenAI-compatible API and no Anthropic one. The same
trade gary-api makes, for the same reason.

The interface is one method wide (`providers/__init__.py`) so that a second
provider is an afternoon's work, and the instruction both would send lives in
`providers/prompt.py` so that a second one cannot quietly drift to a different
version of it. None is implemented, and there is no half-finished one
pretending otherwise.

One tailoring is one call — a resume and a posting in, a resume out — which on
a paid model is a few cents.

```sh
task scout:smoke -- orrery-staff-engineer   # one REAL call, run by hand
```

`smoke` is the only thing here that talks to a model, and it is never part of
`task test`. **It costs nothing by default**: it names a `:free` model, which
exercises this exact path for no money. A paid model is opted into with
`--model`, and the command says what it expects to spend before it spends it.

It has already earned its place. Both of the findings in the ⚠️ table above
came out of its first run, and neither was in any spec beforehand.

## Tests

```sh
task scout:test        # or pnpm --filter scout test
```

Gherkin through behave, driving the real CLI and — for the MCP specs — a real
server subprocess over a real stdio pipe. Alongside them, stdlib unittest for
what the outer surface cannot reach cleanly. Both run under one coverage gate,
set at 100%.

**No tier calls a real model.** The provider is stubbed, so a scenario can
hand tailoring exactly the draft it wants to test — including one that invents
an employer, which is what `features/tailoring.feature` exists for. That is
also the gap `smoke` fills: a stub cannot notice that the prompt stopped
working.
