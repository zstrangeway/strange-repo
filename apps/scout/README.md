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
scout save --url https://example.com/jobs/staff-engineer
# or, for a board that blocks fetches:
pbpaste | scout save --text - --title "Staff Engineer" --company "Orrery"

scout list
scout tailor orrery-staff-engineer
scout log orrery-staff-engineer applied --note "referral from Ada"
scout show orrery-staff-engineer
```

That is the whole tool.

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

That exposes four tools: `save_posting`, `tailor_resume`, `log_status`, and
`list_postings`. The first three are the capabilities; the fourth is there
because a session that can save and tailor but cannot see what it saved makes
you go and read the database by hand.

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
