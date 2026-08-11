# gary-api

A FastAPI service backed by Postgres. It runs the game, and it owns accounts,
the identities that reach them, and sessions. It holds no passwords: Google,
Facebook and Apple authenticate people and gary trusts the result.

Clients are anything — gary-web is a browser app, and an iOS or Android one
would call the same endpoints the same way. Sessions are bearer tokens, never
cookies, which is what keeps that true. `BROWSER_ORIGINS` names the origins a
browser may call from; without it the browser makes the call and then refuses
to hand back the answer.

Session tokens are random and stored only as SHA-256 digests, so a copy of the
database is not enough to impersonate anyone. Two providers naming the same
address are two accounts, deliberately: gary cannot verify an address, so
treating a match as proof would be a way into someone else's account.

`GET /health` reports its own state and the database's, always at 200 — the app
answering is the signal that it is up, and the body carries what it depends on.
It exists for Fly's health check, which is what `fly.toml` calls.

## The game

gary is a game master. A campaign names a system and a module, characters are
made in it, and a turn is something a player says and gary answers.

**The model narrates. It does not decide anything.** Three deterministic
layers sit under it and it proposes into them:

| Layer | Owns | The model may |
| --- | --- | --- |
| `dice.py` | randomness | ask for a roll, never produce one |
| `systems/` | what a system permits, and how a check resolves | ask for a check, never decide its degree |
| `world.py` | what is true in this campaign right now | ask to change it, never claim it changed |
| `narration/` | prose | everything else |

That is why a language model can run a game here without the story drifting:
what it is told at the start of each turn is the world as the event log has
it, not as the last few paragraphs implied.

**The world is an append-only event log, projected on read.** `world_events`
is the truth and there is no snapshot column. `characters` holds the sheet as
created; current hit points and conditions are a fold over what happened, so
"why is Bramble on 3" has an answer that is a list of events rather than a
column somebody overwrote. `GET /campaigns/{id}/history` is that list.

**Systems are pluggable.** One file under `src/gary_api/systems/` carries a
ruleset's data and its behaviour, and adding one is that file plus its entry
in `REGISTRY`. Nothing outside the package names a system —
`tests/test_pluggable.py` fails the build if that stops being true. 5e and
3.5e grade a check two ways; Pathfinder 2e grades it four, with the natural-20
shift, and nothing between the model and the engine knows the difference.

### Playing a turn

`POST /campaigns/{id}/turns` answers `text/event-stream`:

```
event: turn      data: {"turn_id": "…", "role": "gm"}
event: narration data: {"text": "The door groans"}      ← many of these
event: roll      data: {"notation":"1d20+3","dice":[14],"modifier":3,
                        "total":17,"reason":"Perception"}
event: world     data: {"kind":"moved","place":"the belfry stair"}
event: done      data: {"turn_id": "…", "role": "gm"}
event: refusal   data: {"detail":"…","code":"gm_refused"}
event: error     data: {"detail":"…","code":"gm_unavailable"}
```

Everything refusable outright — no session, not your campaign, nothing said,
nobody at the table — is refused before a byte is sent. **After that the
status line is spent**, so a refusal or a failure is an event on the open
stream, not a status. A turn cut off partway is kept and marked incomplete
rather than dropped: the next turn is told the transcript, and a hole in it is
a story that never happened.

### The model

Which model runs a campaign is a per-campaign choice, picked in the UI.
`GET /models` is the menu; the one rule it enforces is **the model must
support tool calling**, because a model that cannot call a tool would narrate
a perfectly plausible game that nothing was adjudicating. Choosing outside
that set is refused with `unsupported_model`.

The live list comes from OpenRouter and is cached for the process. Without a
key, or with OpenRouter unreachable, gary offers a built-in list instead so
the app still starts and still plays.

Narration goes through **OpenRouter, not the Anthropic API** — OpenRouter
serves only an OpenAI-compatible `/api/v1/chat/completions`, so the client is
the `openai` SDK pointed at a different base URL. Two things the direct path
would have given us are simply not there, and both are contained in
`narration/openrouter.py`: typed refusals (a model declining arrives as
ordinary narration, so the `refusal` frame is mostly exercised by the double)
and server-side refusal fallbacks.

### Configuration

| Variable | What it does |
| --- | --- |
| `OPENROUTER_API_KEY` | The key narration needs. Unset means the built-in model list, and a narrator that cannot run. |
| `GM_MODEL` | What a campaign that names no model runs on. Default `anthropic/claude-sonnet-5` — the suggestion list leads with Opus 5, but the thing to suggest first is not the thing to bill by default. |
| `GM_FAKE=1` | Stand in for the model, as `IDENTITY_FAKE` does for the providers. Set by the specs. |
| `DICE_SEED` | Fix the dice, so a spec can assert a number rather than only that a number arrived. |

`report_configuration()` runs at startup, so a missing key is a log line then
rather than something a player discovers mid-sentence.

## Database

Set `DATABASE_URL`; it defaults to `postgresql://postgres@127.0.0.1:5432/postgres`.
A `postgres://` or `postgresql://` URL is upgraded to the async driver
automatically, so a provider's connection string works unmodified.

```sh
pnpm --filter gary-api migrate                    # apply migrations
pnpm --filter gary-api revision "add widgets"     # generate one
```

```sh
pnpm --filter gary-api seed                       # local accounts
```

`seed` migrates, then creates or resets `ada@`, `alan@` and `grace@example.com`.
Re-running is safe and puts a mangled local database back rather than failing on
the duplicate email. It refuses to run unless `DATABASE_URL` looks local,
because those accounts are reachable with a published sign-in code.

Deploys run `alembic upgrade head` as Fly's `release_command`, before the new
version takes traffic. That gates the deploy on reaching the database, so an
unset or wrong `DATABASE_URL` fails the deploy rather than starting a service
that cannot work.

## Run

```sh
pnpm install     # once, from the repo root
pnpm dev         # development, with reload
pnpm serve       # production
```

## Test

Behavior is specified in Gherkin and run with behave; anything not reachable
through the API has a stdlib unittest alongside it. Coverage spans both runs and
is gated at 100%.

```sh
pnpm test
```

**Nothing in the suite ever calls a real model.** Every tier runs with
`GM_FAKE=1`, the same trade already made for Google and Facebook. So the specs
prove gary's handling of a narration and prove nothing about whether
`narration/openrouter.py` talks to OpenRouter correctly — which is the most
likely place for this to be broken while green, because the fragmented
tool-call accumulation is exactly the sort of thing a stub is written to agree
with.

Looking at that gap is a manual step, and never an automatic one:

```sh
pnpm --filter gary-api smoke                                        # one REAL turn
pnpm --filter gary-api smoke -- nvidia/nemotron-3-super-120b-a12b:free
```

It plays one turn against the live API and prints the narration, **which tools
were called and with what**, the token counts and the cost. What it is looking
for is whether the model went *through* the engines rather than narrating
around them — a model that asserts a degree or moves the party in prose alone
produces a game that reads fine and is being adjudicated by nothing.

It needs `OPENROUTER_API_KEY` and it spends tokens, so it is opt-in and
nothing calls it for you. **OpenRouter's `:free` models cost nothing and are
enough to exercise the path** — the two runs so far were free ones, and they
already disagreed with each other, which is the sort of thing this is for.

The suggested set in `narration/models.py` is picked on price and reputation,
not on evidence. Turning that into evidence would mean many runs across many
models, which is a project of its own and not one this repo is doing.
