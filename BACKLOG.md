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

*Last swept 2026-08-29 against `977f5ae`, by running all three tiers, nine
real-model turns across five scenes and three models, and reading the deployed
apps. Every tier was green and nothing below is a failing test — these are
things no test is looking for.*

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

**Run 2026-08-27, same model, on a new `--won` scene** — something overcome,
nothing given for it yet. It found that gary was **never told to award**. The
tool had a description; the system prompt's rules covered dice, world changes,
contradictions and refusals and said nothing about experience, so the model
narrated the aftermath of a kill and called nothing at all. One line in the
prompt fixed it, and the same model on the same scene then awarded 25, and 50
on a third run — both well inside the 300 the bound allows.

Worth generalising: **a tool most models will reach for when the fiction calls
for it does not need a prompt rule; a tool nothing in a turn asks for does.**
Nothing says "and now hand out experience" the way a locked door says "roll for
it". `tests/test_openrouter.py` now pins that gary is told.

The same run also caught this script accusing the model wrongly — it printed
"asked for a roll or check NO ← it decided the outcome itself" about a scene
whose fight was already over. A scene now says whether it has anything to roll,
and the report says whether an award was inside the bound rather than leaving
it in the arguments to be checked by eye.

**Run 2026-08-29, same model, on a new `--fight` scene** — something coming up
the stair, nothing in the fight yet. It found two things, one in this script
and one in gary.

The script first. `begin_combat` answered "a fight began against Zombie" and
`attack` answered "Zombie swung at Bramble" — neither said anything the router
says. The router rolls initiative for both sides and answers with the order;
it resolves a swing against the target's armour and answers "hit Bramble for 7
(15 against 12)". So the model was told neither who was up nor whether its
blow landed, invented both, narrated a miss on its own authority — and the
report printed a clean bill of health. **That is the third time this harness
has been looser than the thing it stands in for**, after the skill-not-an-
ability check and the modifier taken from the model, and it is the worst of
the three: who goes first and whether a blow lands are the two things gary is
explicitly never allowed to decide, so they are the two things a stand-in has
to actually decide. Both now go through `ruleset.initiative` and
`ruleset.resolve`, and both are pinned on a fixed seed.

Then gary — and this one is **not fixed**, so it has its own item below. Re-run
against the honest harness, the model narrated the real numbers — 2, then 7,
then a miss, then 7, matching the four degrees the engine returned. But it also
called `damage` for 7 *after* `attack` had already taken those hit points off,
so one blow cost fourteen and Bramble went down at the wrong time.

Worth keeping alongside the earlier generalisation: **a rule that is right
everywhere else can be the thing that produces the bug.** The model was not
ignoring its instructions here, it was following the one directly above the
one it needed — "you never state that the world changed without recording it
— moving the party, hurting someone" — and nothing told it that `attack` had
already done the recording.

The same run caught the report accusing a model wrongly for the third time —
"asked for a roll or check NO ← it decided the outcome itself" printed
directly above four valid degrees the engine had just handed back, because
only `roll` and `check` counted and an `attack` is graded too.

**Run 2026-08-29, same model, on a new `--close` scene** — a scene that ended
with three things in its prose and none of them in its world. It passed on the
first attempt, which is the first time any of these has: it wrote down the
iron key, moved the party to the belfry, and set `bell-rings` to 4 by updating
the fact that was already there rather than adding a second one beside it. It
stayed inside the closing tool set and came back with a 61-word recap. The
close pass had never been run against a real model before this.

**Runs 2026-08-29, `--fight`, three models, after the tool-schema fix below.**
Four runs, and the double-write did not recur once — against two out of two
before the fix, on the same small model.

| model | tools called | double-wrote |
| --- | --- | --- |
| nemotron-3-super-120b:free | `begin_combat`, then asked the player | no |
| nemotron-3-super-120b:free | `begin_combat`, 5× `attack`, `end_combat`, `award_experience` 25 | no |
| nemotron-3-ultra-550b:free | `begin_combat`, `attack`, stopped at the player's turn | no |
| minimax-m3:free | `begin_combat`, `attack` | no |

**So the answer to "is the model smart enough" is yes, and it was never the
question.** The same free 120B that double-wrote twice out of two now runs a
whole fight: five swings through the engine, four graded degrees it narrated
accurately, the fight ended, and 25 experience awarded inside the 300 bound.
The 550B and minimax added nothing the 120B could not do — they were simply
also correct. What changed between the two sets of runs was the tool schema,
not the model.

Two smaller things from these runs. The 550B and minimax both correctly
stopped at "Your turn." rather than taking the player's action, which is the
rule `world.render` states in its own line and the one most worth not losing.
And the 550B's first attempt came back "Upstream error from Nvidia: Service
temporarily overloaded" — the run reported `UNREACHABLE` and exited 1 rather
than reporting an empty turn, which is the failure path working.

**The lesson from the fight runs, kept after the item itself was deleted:
read the contract before blaming the model.** The double-write looked like a
model ignoring instructions, and a prompt rule was written and failed. It was
neither. `attack`'s description said the rules "say" what a swing costs —
which is about who authors the number, not whether it has been applied — and
never said the hit points come off; `damage` said "take hit points off a
character", which is exactly the job the model believed was outstanding.
Calling both was a correct reading of the contract as written. Prose at the
end of a rules list is not where a tool gets picked; the schema is.

Of everything this file has recorded, three findings were the harness or the
schema being wrong and one — the award — was a genuine gap in what gary was
told. The ratio is not in the model's favour.

An engine-level refusal was considered and deliberately not built. Every
refusal in this codebase is something the rules know: that is not an ability in
this system, it is not their turn, they are already down. "Was this `damage`
redundant?" is a guess at intent, and `combat.feature:191` already specs
`damage` landing on an adversary mid-fight — a swing and a collapsing ceiling
on one target in one turn is ordinary play the engine could not tell from a
double-write. Results now carry the standing number instead ("now on 18 of
22"), which puts the discrepancy in front of the one actor that can correct it
without forbidding a move that may have been right.

**What no run has covered, and what is therefore still unproven:** the
`--opening`, `--won` and `--close` scenes have each been run against one free
model only. `--fight` now has four runs across three, which is the shape the
others want.

### 2. `play.py` is a quarter of the API in one file

1902 lines: the router, twenty Pydantic schemas, the tool dispatch (`_fighting`,
`_run`) and the turn runner. It has absorbed every feature since campaigns —
scenes, the opening, combat, character creation, advancement — and each one
added to the same module rather than beside it. It was 1679 when this entry was
written and the number was left stale for a fortnight, which is item 4 happening
to this file.

Nothing is wrong with it today. It is simply where the next bug will be, and
where a change will be hardest to make confidently. The seams are already
visible in the file: the schemas, the read endpoints, and everything after the
`# ---- playing` divider at line 933 barely reference each other.

### 3. gary-api has no error tracking

Sentry is wired properly on gary-web: a real DSN in `fly.toml`, source maps
uploaded at build with the release pinned to the commit SHA, events tunnelled
through the app's own origin. gary-api has none of it.

**This entry used to say "no alert, no grouping, no stack", and the stack part
was wrong.** `logs.py` catches every unhandled exception in the ASGI middleware
and logs it with `exc_info`, and the formatter turns that into an `error` object
carrying the type, the message and the full formatted traceback — inside the
JSON deliberately, so a stack never trails outside the object. It arrives with
the request id, the method, the path and the duration, and that id already went
back to the browser in `x-request-id`. That is a good 500 record and the entry
should not have implied otherwise.

What is actually missing is narrower, and worth stating precisely because it
changes what would fix it:

- **Retention.** Fly's built-in logs are a live tail over a short rolling
  buffer, not a history. A 500 at 2am that nobody is tailing is gone.
- **Alerting.** Nothing says it happened. You look, or you never find out.
- **Grouping.** The same bug four hundred times is four hundred lines rather
  than one issue with a count and a first-seen.

A log drain to any sink closes the first two more cheaply than an error tracker
does, so "add Sentry" is not the only answer and should not be assumed. What
argues for Sentry specifically is that gary-web is already on it with source
maps and a release pinned to the commit SHA, and gary-api now reports that same
SHA on `/health` — so one commit names the deployed API, the deployed bundle and
every event from either, and a player saying "the turn broke" is one correlated
trace instead of two tools joined by hand. `sentry-sdk` is also already in the
image, pulled in transitively by `fastapi-cloud-cli`, so this would promote
something that already ships rather than add a dependency.

Worth reading alongside the thing the READMEs already admit: gary-web's own log
lines are in the browser console and nobody collects them. Between the two, the
only durable record of a bad turn is gary-api's log, and only if somebody thinks
to look within the retention window.

## Cheap, and stale things get believed

### 4. Only two shapes of document rot are caught

`apps/gary-api/tests/test_documents.py` now checks the two things that are
exact: no document names a `"kind"` the world does not have, and gary-api's
README names every tool in `narration.TOOLS`. Both directions, because they
catch opposite mistakes — a renamed thing leaves the old word behind, and an
added thing leaves the prose describing a smaller app. The second is the one
that actually bit: "there is no combat" named nothing at all, so no scan for
missing names could ever have found it.

It found one on its first run: gary-api's README documented the party-moved
event under the bare name `moved`, which it has not been since adversaries
landed.

It then found this file, because the sentence above originally quoted that bug
in the exact `"kind": …` shape the pattern looks for. The check cannot tell a
document *claiming* a kind from one *quoting* a wrong one, and the fix is to
describe the old name rather than spell it in the shape that means a claim —
cheaper than an allowlist, and an allowlist is the thing that would eventually
be used to silence a real hit.

**A third check was tried and abandoned, so it does not get tried again.**
Verifying that every backticked path in a document exists: 59 of 85 came back
missing and almost all were false — `dice.py` in gary-api's README means
`src/gary_api/dice.py`, `actions/checkout` is somebody else's repo,
`text/event-stream` is a MIME type, and `apps/example-web` is deliberate
history. Resolving those properly is more machinery than the bug is worth.

What is still uncaught is every claim made in a sentence rather than a name. A
README that describes the wrong behaviour in fluent English, with every
identifier spelled correctly, passes all of this.

### 5. Two things dependabot cannot do, now that it is configured

`.github/dependabot.yml` exists: github-actions, npm at the workspace root, uv
for gary-api, and docker for the two base images — monthly, grouped so minor
and patch arrive as one pull request per ecosystem and a major arrives alone.
That is the answer to the ten that were opened against `apps/example-web` and
`apps/example-api` and closed against a repo shape that had already gone.

**The file is valid; whether it produces anything is still unseen.** Dependabot
posted its own `.github/dependabot.yml` check on the pull request that added it
and it passed, which settles the schema — including the `uv` ecosystem name,
which the supported-ecosystems table still does not list and which had to be
taken from the options reference. So the "bad key opens nothing and reads like
a quiet month" risk is gone.

What is left is narrower: nothing has watched a monthly run actually open a
pull request, and a config that parses can still match no manifests. Worth one
look at Dependency graph → Dependabot after the first month, and worth
remembering that the last ten pull requests were closed rather than merged —
this only helps if somebody reads them.

**`superfly/flyctl-actions/setup-flyctl@master` is pinned to a branch.** Both
deploy jobs use it, so the deploy path runs whatever is on that branch on the
day — dependabot has no version to bump and cannot help. Pinning it to a tag
or a SHA is a decision about the deploy path rather than a dependency bump,
which is why it was not made while writing the config.

The three actions the closed pull requests wanted at v7 — `actions/checkout`,
`actions/setup-node`, `astral-sh/setup-uv` — are still at v4, v4 and v5. They
were deliberately not bumped by hand: the current majors could not be verified
from here, and guessing a tag is how a green CI turns red for no reason.
Dependabot will propose them with a changelog attached, which is the better
version of the same change.

### 6. The browser suite's patience is one number now, and still untested

**The old title was wrong and worth correcting: nothing waited fifteen
seconds.** All twenty-seven were *ceilings* on condition waits —
`waitForSelector` returns the moment the thing appears — and the suite gets
through 74 scenarios in about three minutes, which twenty-five real
fifteen-second waits make arithmetically impossible. The cost was never time.

The real smell was twenty-seven copies of `15_000` across five files, so
raising it for a slow machine meant editing all twenty-seven and nobody did.
It is `PATIENCE` in `features/support/hooks.mjs` now, overridable with
`E2E_PATIENCE_MS`, so a loaded CI runner can be given longer without a line of
test code changing.

**Two causes behind the old timeouts were real bugs rather than slowness**, and
that is the lesson to keep: every one of those failures reported a timeout and
none of them was about time. The stub's turn gate dropped a release that
arrived before the turn reached it — deadlock, not latency. And `scenes.current`
raced itself into an unhandled 500, so the browser waited out the clock on a
page that was never going to change.

What is left is genuinely unexplained: `say` could click and have nothing reach
the screen. It confirms the send and clicks once more before giving up, which
converts a lost click into a real message but does not say *why* it was lost,
and the textarea being uncontrolled rules out the obvious answer. Nobody has
raised `E2E_PATIENCE_MS` and watched whether that makes it go away, which is
now a one-variable experiment and would at least say whether it is time or not.
