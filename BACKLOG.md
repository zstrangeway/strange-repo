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

*Last swept 2026-08-22 against `d29fcde`, by running all three tiers and reading
the deployed apps. Every tier was green; nothing below is a failing test.*

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
whether the model went *through* the engines or narrated around them. There is
nowhere in the repo that answers "when did this last work against a real model",
which is why nobody can tell whether it does.

### 2. `play.py` is a quarter of the API in one file

1679 lines: the router, twenty Pydantic schemas, the tool dispatch (`_fighting`,
`_run`) and the turn runner. It has absorbed every feature since campaigns —
scenes, the opening, combat, character creation — and each one added to the same
module rather than beside it.

Nothing is wrong with it today. It is simply where the next bug will be, and
where a change will be hardest to make confidently. The seams are already
visible in the file: the schemas, the read endpoints, and everything after the
`# ---- playing` divider at line 933 barely reference each other.

### 3. eslint runs nowhere

Not in any CI job, and not in any `test` task — `gary-web:test` is `unit` then
`cucumber-js`, and the root `test` is the three apps' test tasks. So `pnpm lint`
is something a person has to remember, which means it is something nobody does.

One warning is outstanding as of this sweep: `src/app/(app)/campaigns/[id]/page.tsx:271`,
a `useEffect` with no dependency array. It is guarded by the `opening` ref so it
cannot open twice, but it re-evaluates on every render.

A lint gate that is green from the day it is added is worth more than the one
warning it is currently hiding.

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

### 6. Three documents describe an app that changed underneath them

- `apps/gary-api/README.md`, **Who plays whom**: "⚠️ There is no combat, so 'the
  player controls them in a fight' is not a thing yet. There is no initiative and
  no turn order." The **Fights** section thirty lines above documents initiative,
  turn order and four combat tools. One of the two is wrong and it is this one.
- `apps/gary-api/fly.toml:30`: "gary-web reaches this app over Flycast." It does
  not, and has not since the browser started calling gary-api directly. The
  conclusion — safe to scale to zero — still holds, via the public proxy; the
  reason given for it does not, so anyone reasoning from it will reason wrongly.
- `apps/gary-web/README.md:8`: "There is no server rendering and no server of its
  own." `next.config.ts` is `output: "standalone"` and the image runs a Next
  server. Every route is static and every gary-api call is made from the page, so
  the point being made is true and the sentence making it is not.

### 7. Dependency drift, and nothing to drive it

There is no `.github/dependabot.yml`. Ten Dependabot pull requests were opened
and all ten were closed unmerged — several of them against `apps/example-web`
and `apps/example-api`, which no longer exist, so they were closed against a repo
shape that had already gone rather than judged on their merits.

CI still pins `actions/checkout@v4`, `actions/setup-node@v4` and
`astral-sh/setup-uv@v5`, against v7, v7 and v7 proposed. Either configure
Dependabot for the paths that exist now, or bump the three actions by hand and
accept that this is manual.

### 8. The browser suite waits a fixed fifteen seconds, twenty-five times

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
