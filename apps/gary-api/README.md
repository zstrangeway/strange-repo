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

### Scenes

Play is divided into scenes, and a scene is the unit of gary's memory. What
the model is told each turn is **this scene's turns plus the recaps of the
ones before it** — never every word since the campaign began. Without that a
campaign costs more per turn the longer it runs, without limit, and what
eventually breaks is not the bill but the model's grip on a context it cannot
hold.

So a boundary is where **prose stops being memory**. Across one, what carries
is the world as the log has it and a few sentences a scene.

Which makes closing a scene the last moment at which something narrated but
never recorded can still be recorded — and that is what the close pass is for.
It reads the scene, records what the world is missing, and writes the recap.
**It is not a licence to assert**: it proposes into the same engines, through
the same runner a turn uses, and is refused by the same refusals. It is
offered fewer tools, not looser ones — no dice and no checks, because a die
thrown after the fact decides something nobody was there for.

A scene ends three ways: gary asks (the `scene` tool), the player says
(`POST /campaigns/{id}/scenes`), or it has run past `SCENE_TURNS` or
`SCENE_CHARS` and the engine breaks it regardless. That last one is the point
— a bound a model can decline to apply is not a bound. A boundary always lands
*after* a turn, never inside one.

A scene closes even when gary cannot be reached to say what happened in it,
and its recap is then null. A campaign missing a paragraph is worse than one
with it; a campaign whose context never stops growing is worse than both.

⚠️ **Recaps still accumulate.** This makes growth roughly 50× slower, not
zero. The next lever is recapping the recaps, and it is not built.

### The opening

A campaign with a party and nothing said is a table where everyone has sat
down and nobody has spoken, so gary speaks first. `POST /campaigns/{id}/opening`
is a turn like any other — streamed, stored, in the first scene, reaching the
same engines — and the only unusual thing about it is having no player message.

A second one is refused with `already_begun`, which is what makes it safe for a
client to ask for on sight of an empty transcript rather than having to be
certain first: a reload and a second tab both reach this and neither knows
about the other. A failed opening leaves the campaign openable, because half a
turn stored here would make it look begun and nothing would ever open it
properly.

A module carries a **premise** and a **hook**, and they answer different
questions: the premise is a situation in the world, the hook is why this party
is standing in it tonight and who wants it dealt with. Without the second one
gary opens on scenery, and — asked "why am I here?" — hands the question back:
*"perhaps you have your own reasons"*. That is the one thing a game master may
not say, so the module says why instead, and the system prompt draws the line
explicitly: the world is gary's, the character's choices are the player's.

`GET /campaigns/{id}` carries `premise`, `hook` and `place` alongside `begun`,
so a client can put a situation on screen for free while the opening is still
being written.

### Playing a turn

`POST /campaigns/{id}/turns` answers `text/event-stream`:

```
event: turn      data: {"turn_id": "…", "role": "gm"}
event: narration data: {"text": "The door groans"}      ← many of these
event: roll      data: {"notation":"1d20+3","dice":[14],"modifier":3,
                        "total":17,"reason":"Perception"}
event: world     data: {"kind":"moved","place":"the belfry stair"}
event: scene     data: {"scene_id":"…","title":"The road north","number":2}
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
| `SCENE_MODEL` | What closes a scene. Default `anthropic/claude-haiku-4.5` — recapping is summarising, not running a game, and it is the one call nobody reads a sentence at a time. |
| `SCENE_TURNS` / `SCENE_CHARS` | When a scene is broken whatever anybody thinks. Default 20 turns, 24000 characters. |
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
pnpm --filter gary-api smoke -- --opening                          # the opening instead
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
