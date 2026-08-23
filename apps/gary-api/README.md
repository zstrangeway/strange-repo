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
in `REGISTRY`. Nothing outside the package names a system — and nothing
outside it names a system's *vocabulary* either. `tests/test_pluggable.py`
fails the build on both.

That second half was added after the first one turned out not to be enough:
nothing named a system, and the router still spelled `"con"` to find hit
points and `"str"` to find an attack bonus, and kept an armour class, an
unarmed damage die and a starting score of its own. A system with different
abilities would have needed the router changed to add it, which is exactly
what one file per system is supposed to prevent. 5e and
3.5e grade a check two ways; Pathfinder 2e grades it four, with the natural-20
shift, and nothing between the model and the engine knows the difference.

### Making a character

**Which methods exist is the system's to say.** Not a global list with
exceptions: an edition permits what it permits, the player picks from what
their edition permits, and asking for one it does not offer is refused the way
an unknown class is.

| System | Generates | Types in |
| --- | --- | --- |
| D&D 5e | the standard array · 4d6 drop lowest · point buy | ✓ |
| D&D 3.5e | 4d6 drop lowest · point buy | ✓ |
| AD&D 1e | 3d6 in order · the DMG's Method I | ✓ |
| Pathfinder 2e | nothing, and says why | ✓ |

Offering is not generating, which is why `Method.generates` is a separate
question from being on the list: point buy is a method an edition permits and
gary produces no numbers for. `arrange` is the third question — rolling three
dice down the page generates without arranging, and typing them in is the
reverse.

`POST /campaigns/{id}/scores` rolls a set. **The dice are gary-api's and not
the client's**, for the reason they are not the model's: a number a browser
sent is a number somebody typed. Nothing is stored — a set nobody made a
character out of is not a fact about the campaign — which is also why rolling
again is free and never refused.

**Hit points** are the class's hit die plus the constitution modifier, floored
at one, because a constitution penalty can be worse than a hit die is big and
a character created already dead is nobody's idea of a rule. A class with no
hit die typed in yet gets the system's default, which is a gap rather than a
rule and reads as one.

⚠️ **The point buy budget is a construction aid, not a gate.** The costs and
the budget are published so a client can count the spend while you make
choices; what finally arrives is range-checked like any other score. Anybody
determined to hand-post an illegal spread can, and is only cheating
themselves.

⚠️ **No racial or ancestry modifiers, and no class minimums.** 1e will not
stop you playing a paladin with a charisma of 9, and multiclass requirements
do not exist.

### What a roll says

A roll carries **whose it is** and **what it was against**. Both `roll` and
`check` take a character; `roll`'s is optional, because a roll about how sound
the timbers are belongs to nobody and a name invented to fill the field would
be worse than the gap. It is stored as `rolls.character_id`, so "everything
that happened to John" is a join rather than a string match.

Before this, only `check` carried a name and only as far as the engine — the
`rolls` table had nowhere to keep it, so the stream said whose a check was and
a reload did not. Gary had noticed and was working around it by writing the
name into the reason: *"John falling damage"*, a mechanical fact in a
free-text field where nothing can check it.

**`check` takes a list.** One hazard at one difficulty is one thing happening,
however many people are standing in it. Asked one at a time it cost a round
trip each, and a party of four crossing rotten planks reached the round cap
describing a single moment. Each of them still rolls separately and is stored
separately; what changed is how many times gary has to ask. A name nobody at
the table has refuses the whole call — half a check applied says two of them
crossed when the fiction says they went together.

**A check names an ability, never a modifier.** `check` was offered
`character`, `dc` and `reason` and no modifier at all, so every check ever
graded was a flat d20 — a fighter and a wizard fell off the same plank equally
often. The fix is not to let gary supply the number: what a score is worth is
a rule, and the score is on a sheet gary does not own. Gary names `dex`, the
sheet gives the score, and `Ruleset.modifier()` says what that is worth.

Which makes it per-system, and it is: `add-1e` returns 0 from `modifier()` on
purpose. First edition has a different table per ability and no general
ability check to spend one on, so handing back `(score - 10) // 2` would be
quietly running third edition in a first edition game. Zero until somebody
types the real tables in.

### Fights

**Order and outcome are the engine's.** Gary says who is fighting and what
somebody tries; it never says who goes first, whether a blow lands, or what it
cost. Four tools — `begin_combat`, `attack`, `end_turn`, `end_combat` — and
the fight itself is three world events, so whose turn it is and which round
are folded out of the log exactly as hit points are. There is no fight table
to drift.

Gary still authors the monster, because choosing what you fight is the one
genuinely authorial thing in a fight and there is no bestiary to look one up
in. From there it is an `adversaries` row and what happens to it is the
engine's — damage, healing and conditions all reach either side.

**Gary is told the order, the round and whose turn it is on every turn**, and
told to stop when the order reaches the player's character. It may not end
their turn. Taking it ends it: a turn holds one action, so an attack advances
the order by itself, which is also the only reason a fight can ever move past
the player at all.

`add-1e` refuses fights outright. First edition rolls one d6 per *side* and
moves whole sides at a time — a different shape from the flat order everything
here assumes, not a different number in it — so approximating would log
something that never happened at a first edition table.

⚠️ **Not built, and deliberately:** movement, range and positioning; spells
and resources; reactions and opportunity attacks; criticals; death saves. A
fight is initiative, attacks, damage and down. Two shortcuts worth knowing:
a character's armour class is a stated default because sheets have no armour,
and a monster's initiative modifier is its attack bonus, which is not a rule
anybody plays by.

### Advancement

**Gary awards experience. It never awards a level.** The precedent is
`damage`: gary already names a number and the engine applies it, so naming
what something was worth is authorship it already has. What that adds up to,
when it crosses a threshold and what a level is worth are rules, so the system
says them and the engine writes them down. There is no tool that grants a
level, and `tests/test_pluggable.py` fails the build if one ever appears.

So an award is **two events, not one**. `experience-gained` is what gary
proposed; `level-gained` is the engine's answer to it, and carries hit points
the engine rolled. Folding them together would put dice inside gary's event,
and a fold that rolls dice answers differently every time the log is replayed
— which is the one property `world_events` exists to have.

`characters.experience` is the sheet, like `max_hp`: a character made at level
3 is created holding whatever level 3 costs, so being made there and earning
your way there are the same character afterwards. Everything since is the log.
`GET /campaigns/{id}/world` is therefore where a current level comes from;
`GET /campaigns/{id}/characters` is the sheet and does not move.

| System | Level 2 costs | Stops at |
| --- | --- | --- |
| D&D 5e | 300 | 20 |
| D&D 3.5e | 1000 | 20 |
| Pathfinder 2e | 1000 | 20 |
| AD&D 1e | refuses | — |

⚠️ **First edition refuses to price a level at all.** It does not have an
advancement table, it has one per class — a fighter reaches second level at
2,000 and a magic-user at 2,500, and they keep diverging. Lending them a
shared curve would be quietly running third edition, which `modifier()`
already declines to do; typing eleven tables in from half-memory would be
worse, because wrong numbers look exactly like right ones. Filling it in means
widening the interface too: every question would have to take the character's
class, which no other system needs.

**One award is worth at most one level.** Damage is bounded by a fight and
experience is bounded by nothing, so without a bound a model having a strange
turn could hand out ten thousand and jump four levels in a sentence. The
system says the most, measured from where somebody is, and a dungeon worth
three levels arrives as three awards — which the log then shows line by line.

⚠️ **The close pass may not award.** A level rolls a hit die, and closing a
scene is the one tool set with no dice in it: a die thrown there decides
something nobody was there for. Experience for a scene's last fight is the
next turn's to give.

### Who plays whom

Exactly one character in a campaign is the player's; the rest are companions,
and gary both speaks for them and does what the player tells them to. That is
`characters.played_by`, `"player"` or `"gary"`, set at creation with
`{"mine": true}` and moved afterwards with
`POST /campaigns/{id}/characters/{character_id}/player`, which answers the
whole party because the character that used to be the player's changed too.

Three refusals fall out of "exactly one", and they are worth telling apart:

| Code | When |
| --- | --- |
| `already_playing` | making a second `mine` character — take over instead |
| `no_party` | playing a campaign nobody is in |
| `no_character` | playing a campaign where none of them is the player's |

The last one is the reason it is a field rather than a convention. Gary is
told, per member of the party, which of them is its to voice and which is
**played by the player — never decide what they do**, and a party where that
sentence is true of nobody is one gary would narrate straight through. Better
refused before the money is spent than answered by a game master playing
everyone including you.

**In a fight, this is the field the order hangs off.** Gary is told the
initiative order, the round and whose turn it is, and told to stop when the
order reaches the character `played_by` says is the player's — so a companion
is gary's to move and the player's to direct, and the one character that is
yours is never taken for you. Outside a fight it is the same arrangement in
prose rather than in turns.

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

**A turn is several requests, not one.** A tool call ends a completion, so
what the engines answered has to go back in before the model can carry on.
`ROUNDS` caps how many times that may happen, and it is a ceiling on the cost
and the wait of a single turn rather than a free dial.

It was eight, and eight was too few: a party of four crossing one hazard is
four checks plus the damage that follows, and models ask for those one at a
time rather than together, so an ordinary moment reached the wall. Reaching
it used to end the turn in silence — the loop fell out of the bottom having
narrated nothing, which reads as the app freezing rather than as a turn
ending. **The last round is now spent narrating**: tools are still described
but forbidden with `tool_choice: "none"`, and gary is told to say what
happened with what it already has. A model still calling tools through that
is a `NarrationError`, because the player is owed an answer.

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
pnpm --filter gary-api smoke                                    # one REAL turn
pnpm --filter gary-api smoke --opening                          # the opening instead
pnpm --filter gary-api smoke nvidia/nemotron-3-super-120b-a12b:free
```

It plays one turn against the live API and prints the narration, **which tools
were called and with what**, the token counts and the cost. What it is looking
for is whether the model went *through* the engines rather than narrating
around them — a model that asserts a degree or moves the party in prose alone
produces a game that reads fine and is being adjudicated by nothing.

No `--` before the arguments. The `smoke` script is `task smoke --`, and pnpm
passes a second `--` through literally rather than eating it, so
`smoke -- <model>` arrives as `task smoke -- -- <model>` and `--` is taken as
the model name. It fails with `'--' is not a valid model ID`, which reads like
a bad model rather than a bad command line.

It needs `OPENROUTER_API_KEY` and it spends tokens, so it is opt-in and
nothing calls it for you. **OpenRouter's `:free` models cost nothing and are
enough to exercise the path** — the two runs so far were free ones, and they
already disagreed with each other, which is the sort of thing this is for.

The suggested set in `narration/models.py` is picked on price and reputation,
not on evidence. Turning that into evidence would mean many runs across many
models, which is a project of its own and not one this repo is doing.
