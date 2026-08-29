# Backlog

What is known to be wrong, thin, or drifting. Ordered by what it would cost to
find out the hard way rather than by effort.

**Things deliberately not built are not in here.** They are in the app READMEs,
marked ⚠️, beside the code that would change if they ever were — movement and
spells in a fight, recaps of recaps, racial modifiers, first edition's ability
tables. This file is for things that ought to change; those are things that were
decided. Moving them here would make two places to look and one of them wrong.

An item says how it was found, so it can be re-checked rather than argued about.
When one is done, delete it — the commit is the record.

*Last swept 2026-08-23 against `c8f5bd2`, by running all three tiers, a real
model, and reading the deployed apps. Every tier was green; nothing below is a
failing test. Item 8 was added on 2026-08-29 when scout landed, and rewritten
the same day once its smoke check had actually been run.*

## Worth real work

### 1. Nothing has ever run the real narrator on purpose

`narration/openrouter.py` is 643 lines of SSE framing, fragmented tool-call
argument accumulation, retries and the last-round `tool_choice: "none"` pass,
and **no tier exercises any of it** — all three run `GM_FAKE=1`. The double was
written from the same understanding as the code it stands in for, so it agrees
with it by construction. This is the most likely thing in either app to be
broken while everything is green, and gary-api's README already says so.

`pnpm --filter gary-api smoke` is the only thing that looks. It is opt-in, needs
`OPENROUTER_API_KEY`, and on a `:free` model it costs nothing and exercises the
same path. It has been run twice ever, both times on free models, and **the two
runs disagreed with each other**.

What is missing is not a feature, it is a habit and a record: run it before any
deploy that touches `narration/`, and write down the date, the model, and
whether the model went *through* the engines or narrated around them.

**Run 2026-08-22, `nvidia/nemotron-3-super-120b-a12b:free`, an ordinary turn.**
Called `check` (int, dc 14) and took the degree from the rules, then `remember`
and `move_party`. Went through the engines on all three — nothing asserted in
prose. 91 words in 27 pieces, so the streaming path holds. $0.00000.

Part of why it had only been run twice is now known: two of the three
invocations the README documented did not work. The `smoke` script is
`task smoke --` and pnpm passes a second `--` through literally, so
`smoke -- <model>` made `--` the model name and failed with `'--' is not a
valid model ID` — which reads like a bad model rather than a bad command line.
Fixed in the same commit as this note.

**Run again 2026-08-23, same model, after advancement landed.** The turn still
works with a fifteenth tool offered. It also caught something in this script
rather than in gary: the model asked for a check against `investigation` — a
fifth edition *skill*, not an ability — and `run_tool` graded it and printed
"degree from the rules (valid)". The router refuses that outright, so the run
reported a model going through the engines when production would have sent it
back. It was taking a `modifier` from the model too, which the router never
does. Both fixed, both now unit-tested. **A harness looser than the thing it
stands in for reports the wrong answer confidently**, and that is worth
re-checking whenever the router gains a refusal.

**What no run has covered, and what is therefore still unproven:** a fight
(`begin_combat`, `attack`, `end_turn`, `end_combat`), the scene close pass, the
opening, and now `award_experience` — whose bound is the one thing about an
award worth watching a real model for. The last needs a scenario this script
does not have: its two are a search and an opening, and neither has overcome
anything. Adding a third means turning the `opening` flag into a named scene,
which `tests/test_smoke.py` is coupled to in about a dozen places.

### 2. `play.py` is a quarter of the API in one file

1679 lines: the router, twenty Pydantic schemas, the tool dispatch (`_fighting`,
`_run`) and the turn runner. It has absorbed every feature since campaigns —
scenes, the opening, combat, character creation — and each one added to the same
module rather than beside it.

Nothing is wrong with it today. It is simply where the next bug will be, and
where a change will be hardest to make confidently. The seams are already
visible in the file: the schemas, the read endpoints, and everything after the
`# ---- playing` divider at line 933 barely reference each other.

### 3. `packages/ui` is linted by nothing

gary-web's lint is now a gate: `--max-warnings 0`, run first inside its `test`
task, so it fires wherever the specs do — CI included. That leaves one hole.

Nothing lints `packages/ui`. eslint run from `apps/gary-web` refuses those
files by name because they sit outside its config's base path, so the twenty
four components in there have never been linted at all. Its `lint` script used
to name a task that did not exist, which is how nobody noticed; the task now
exists and says out loud that it lints nothing.

Closing it means either an eslint of its own in that package — a dependency,
so worth agreeing before adding — or moving gary-web's config up to the
workspace root so its base path covers both. The second is cheaper and changes
what every existing rule applies to, which is the part to look at first.

### 4. The tier that exists to catch drift does not reach the newest work

`test:e2e` covers sign-in, identity, profile, one campaign with one turn, and a
reload — nine scenarios. It does not touch combat or the score methods, which
are the two most recent and most intricate features.

Combat is 22 scenarios in gary-api, 2 in gary-web, and 0 end to end. Both web
scenarios run against the stub, which is precisely the thing the README says
cannot notice gary-api and gary-web drifting apart. The score methods are the
same shape: `/catalogue/{slug}` publishes what an edition permits, whether gary
rolls it and whether the results are yours to arrange, and only the stub's
version of that contract is ever checked by a browser.

Keep the tier small — that is its design — but a fight and a rolled set of
scores are the two contracts most worth one scenario each.

### 5. gary-api has no error tracking

Sentry is wired properly on gary-web: a real DSN in `fly.toml`, source maps
uploaded at build with the release pinned to the commit SHA, events tunnelled
through the app's own origin. gary-api has none of it. A 500 in the turn runner
is a JSON line in Fly's log buffer and nothing else — no alert, no grouping, no
stack.

Worth reading alongside the thing the READMEs already admit: gary-web's own log
lines are in the browser console and nobody collects them. Between the two, the
only durable record of a bad turn is gary-api's log, and only if somebody thinks
to look within the retention window.

## Cheap, and stale things get believed

### 6. Nothing catches a document going stale

The three that had drifted are fixed: gary-api's README no longer says there is
no combat thirty lines below the section describing combat, `fly.toml` no longer
explains a scale-to-zero by a Flycast route the browser stopped using, and
gary-web's README now says what its server actually does rather than that it has
none.

What has not changed is that all three were found by reading, months late, and
nothing would have caught any of them. Two of the three were wrong the moment a
commit landed, and both commits were green.

There is no cheap general answer here — prose cannot be type-checked — but the
specific shapes are catchable. A README that names a tool, an endpoint or an
event kind that no longer exists is a grep. `tests/test_pluggable.py` already
does exactly this for system names in source; the same crude scan over the
markdown would have caught "there is no combat" the day `begin_combat` landed.

### 7. Dependency drift, and nothing to drive it

There is no `.github/dependabot.yml`. Ten Dependabot pull requests were opened
and all ten were closed unmerged — several of them against `apps/example-web`
and `apps/example-api`, which no longer exist, so they were closed against a repo
shape that had already gone rather than judged on their merits.

CI still pins `actions/checkout@v4`, `actions/setup-node@v4` and
`astral-sh/setup-uv@v5`, against v7, v7 and v7 proposed. Either configure
Dependabot for the paths that exist now, or bump the three actions by hand and
accept that this is manual.

### 8. scout's grounding check has been run against one model, once

It has now seen real drafts — three runs on 2026-08-29, all
`nvidia/nemotron-3-super-120b-a12b:free` through OpenRouter, against the
example master resume and one saved posting. `pnpm --filter scout smoke`
costs nothing by default, so this is cheap to repeat and should be repeated
before anything that touches `grounding.py` or `providers/prompt.py`.

**Run 1 found two things no spec had thought of, and both are now fixed:**

- The model gave the second employer the first one's dates — Thornfield
  Systems shown as 2021–2025, which are Wilding Labs'. Every year in the draft
  appeared somewhere in the master, so nothing caught it. `grounding.py` now
  checks dates against the employer they sit under.
- The summary reported a deleted bullet and an unrelated promoted one as a
  *rewrite* of each other, because `difflib` aligns by position. The summary
  is the only defence against inflation, so one that invents an edit is worse
  than one that says less. It now compares by content.

**Run 1 also showed the inflation gap doing exactly what the README says.**
The posting asked for "deep Postgres experience"; "ran the Postgres upgrade"
came back as "applied deep Postgres expertise to". No new employer, skill or
title, so the check passed it — correctly, by its own definition — and the
summary showed it. That is the design working, not a defect, and it is the
reason the summary is not optional.

**Run 3, after both fixes, was clean**: six honest rewrites, no invention, no
date corruption, and a summary in which every reported pair was genuinely a
rewrite of that line.

Two more were found the same way — by pointing scout at real Greenhouse and
python.org boards rather than at fixtures — and are now fixed: a board's
**index page** saved silently as a posting, and the MCP save tool told a model
to "use the edit command", which only existed on the command line. Both have
scenarios now.

What is still thin:

- **One model, one posting, one resume.** The example master is the only
  document the check has ever been run against in anger, and it is the one
  shaped to suit it. A real resume with a different heading style is the
  obvious next thing to try.
- **The paid model has never run.** `anthropic/claude-sonnet-5` is the
  default and no call has ever been made on it; every run has been on the
  free model. That is now one model id apart rather than one client apart —
  the direct Anthropic provider was deleted as a second way to reach models
  the router already reaches — so it is a `--model` away whenever somebody
  wants to spend the few cents.
- **The check is not trigger-happy, and that is measured now.** Six free
  models were pointed at a real Greenhouse posting and the example master on
  2026-08-29; two were unavailable (429, 403 — both surfaced as ordinary
  refusals, which is worth knowing on its own) and four produced drafts. All
  four were accepted, none wrongly. So the false-refusal rate is zero over
  four, which is thin evidence but the right sign.

- **⚠️ One of those four invented something and the check passed it.** Not a
  name — a claim. It appended clauses to bullets it otherwise kept:
  "demonstrating experience managing large-scale distributed systems",
  "applying engineering rigor to fast-paced deployment cycles",
  "strengthening core software engineering capabilities". None of those
  phrases is anywhere in the master resume. No new employer, title, skill or
  date, so nothing in `grounding.py` had anything to catch, and the summary
  showed the rewrites, which is the only reason it is visible at all.

  This is the same family as the "deep Postgres expertise" case but a step
  worse: an intensifier is a stronger version of a claim that was there,
  whereas "experience managing large-scale distributed systems" is a claim
  that was not. It is the strongest argument yet that a name-based check
  under-covers what "never invents experience" was meant to mean, and it is
  a product decision rather than a defect — the check does exactly what it
  is documented to do.

  Two of the other four barely changed anything at all, which is its own
  finding about small free models: a tailoring that returns the master
  unchanged is accepted and useless.

### 9. The browser suite waits a fixed fifteen seconds, twenty-five times

`features/rolls.feature:21` ("A roll says whose it is") failed once during this
sweep on a `waitForFunction` timeout at `play.steps.mjs:43`, and passed on a
full re-run — 68 of 68, with CI green on the same commit. A flake, not a defect.

But it is not one step: there are 25 `timeout: 15_000` waits across
`auth.steps.mjs`, `play.steps.mjs` and `fullstack.steps.mjs`, and each is an
independent chance for a loaded machine to fail a run that is not testing
latency. The one that flaked waits for the player's own message to appear after
clicking send, which is the shortest real wait in the suite and so the first to
go. Worth raising the timeout, or waiting on the element rather than on
`document.body.innerText`, before it costs somebody an afternoon.
