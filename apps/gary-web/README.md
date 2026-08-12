# gary-web

A Next.js companion to gary-api. It signs people up and in, and it is where
the game is played: signing in lands on your campaigns, starting one picks a
system, a module and a model, and a campaign page is the table — the party as
the world currently has them, the transcript, and a composer.

It runs entirely in the browser. There is no server rendering and no server
of its own: every route is static, every call to gary-api is made from the
page, and the session is a gary-api token in `localStorage`.

That is a trade, not a free win. The token is readable by any script on the
page, so an XSS bug is a stolen session rather than a defaced one — the price
of having no server to hold an httpOnly cookie.

**Two things follow that will otherwise waste your time.** gary-api must name
this app's origin in `BROWSER_ORIGINS` or the browser makes every call and
then refuses to hand back the answer. And gary-web's own log lines are in the
browser console, not in any server log — nobody collects them.

## Scenes on screen

A scene is where gary's memory ends, so the table draws the seam. Above a
boundary is the story; below it is what gary is actually working from, and a
closed scene shows its recap because that recap is now the whole of what gary
remembers of it. An undivided scroll would hide the most consequential thing
about a long campaign.

Breaking a scene by hand is the one control here that is slow on purpose — it
runs a whole pass through a model — and the button says so while it waits.

## Building the party, then being dropped into it

Starting a campaign lands on `/campaigns/{id}/party`, not on the table. The
table used to be where you made characters, which meant it loaded with an
empty transcript, a disabled composer and "gary is setting the scene" while
gary was doing nothing of the sort — because there was nobody to set it for. A
screen that cannot proceed should be about the thing it is waiting for.

So the party page is that thing. The first character you make is you; every
one after is a companion, and a companion can be taken over with the control
beside its name. There is no pair of radio buttons for the first one, because
at the moment it is made there is only one sensible answer. "Take them in" is
shut until one of them is yours, and a campaign whose party was never built
sends you back here rather than showing a table it cannot lay.

Past that, the game starts happening to you. The campaign page asks gary to
open the scene the moment there is a party and nothing said — no button,
because having made a character, being asked to also press start is the same
empty box in a smaller frame. It is safe to ask on sight: gary-api refuses a
second opening, so a reload or a second tab cannot produce two or spend twice.

The module's premise and hook are on screen immediately, which costs nothing
and covers the seconds the opening takes to arrive. They come off the screen
once the opening lands, since by then they say the same thing twice and the
worse prose is the one that was free.

## Making a character

The party page asks how the scores are decided before it asks for a name,
because that is where a character stops being one. **Which methods are on the
list comes from the system** — `/catalogue/{slug}` says what the edition
permits, whether gary rolls it, and whether the results are yours to place.
A list in this app would be a second place for the rules to live and the
first one to go stale.

So the same control covers four shapes without knowing any of their names:
something to roll when the method generates, boxes to fill when it lets you
arrange, read-only boxes when it does not (three dice down the page is the
whole of first edition's character creation), and a running total when the
system has a point buy. Rolled scores show the dice and the one thrown away,
not just the total — "15" and "6, 5, 4 and a discarded 1" are different things
to read while you decide where to put it.

Nobody has to place any. A character made with nothing gets the system's
default score, which is what every character made before this existed has.

## A fight on screen

While there is one, the only question on screen is whose turn it is, so the
order goes above the party with a marker on whoever is up and the round beside
it. Yours says so in words as well, because the others are gary's to move
through on its own and it stops at you — a page that did not say that would
leave you waiting for a turn that had already arrived.

Nothing here decides anything. The order was rolled by the engine and where it
is up to is folded out of the log, so this renders a fact rather than tracking
one. A monster's roll is set in italic muted text off the `side` the frame
carries, rather than off a list of names the page would have to keep.

## Streaming a turn

A turn arrives as it is written, over SSE. **`EventSource` cannot be used**,
and it is worth knowing why before reaching for it: the session is a bearer
token in `localStorage` — deliberately, because a gary-api cookie would be
third-party to this app and dropped by Safari and Firefox — and `EventSource`
cannot set an `Authorization` header. So `src/lib/play.ts` is `fetch`, a
`ReadableStream`, a `TextDecoder` and a small SSE parser. That parser is a
plain module on purpose: it is the branchy part, and `src/lib` is where the
coverage gate can see it.

Two consequences show up in the UI rather than in the network tab. Anything
that goes wrong after the first byte is a frame, not a status, so a refusal
renders in the transcript instead of as a broken page. And a roll is rendered
as its own element rather than as prose — rendering it as a sentence would
make it indistinguishable from a number the model made up, which is the
distinction the whole design rests on.

## Reading a roll

A card leads with **whose** roll it is, because that was what was missing: a
turn where four people crossed a collapsing causeway showed seven numbers and
no way to tell which neck was out. Then what it was for and how the total was
reached — `rolled 9 + 3 dex = 12` beside `1d20+3 → 12 vs 12` — so a call that
close can be checked by eye rather than taken on trust.

A **graded check always shows its faces**, even when nothing was added to
them. Suppressing that was the first version's mistake and it hid the working
on every check anybody had actually made — a new sheet is straight tens, tens
are worth no modifier, so no check ever had one. `1d20 → 12 vs 12` asks you to
take on trust that the 12 was the die rather than something already adjusted,
and a check decided by a single point is where that trust is worth least.

A **bare roll** still stays quiet when it has nothing to add, because `rolled
5` beside `1d6 → 5` is the same number twice and a busy turn carries seven of
them. Both rules live in `src/lib/rolls.ts` rather than in the component,
because they are the branchy part and `src/lib` is where the coverage gate can
see them.

If the narration ever arrives all at once in production while streaming fine
locally, the thing in front of gary-api is buffering `text/event-stream`.

## Run

```sh
pnpm install     # once, from the repo root
pnpm dev         # development
pnpm build       # production build
pnpm serve       # production server
```

Set `NEXT_PUBLIC_GARY_API_URL` to point at gary-api. It defaults to
`http://127.0.0.1:8000`.

It is baked into the bundle by `next build` rather than read at runtime,
because a browser has no environment to read. Setting it on the running app
changes nothing; it has to be a build arg, and the Dockerfile takes one.

## Test

Behavior is specified in Gherkin and run with cucumber-js against a real
Chromium via Playwright. The suite starts its own Next server and a stub
gary-api, so nothing needs to be running first.

```sh
pnpm unit          # src/lib only, with its coverage gate
pnpm test          # the above, then the browser specs against the stub
pnpm test:e2e      # against a real gary-api and a throwaway database
```

`pnpm unit` is Vitest over **`src/lib` and nothing else**, gated at 100%
including branches. That scope is deliberate: everything outside `src/lib` here
is a React component, and [Next's own testing
guide](https://nextjs.org/docs/app/guides/testing) recommends covering those
end to end rather than with unit tests. A gate that swept them in would report
a number it had not earned. `src/lib` is plain modules, which is where the
branchy logic — error mapping, empty bodies, token handling — actually lives.

`test:e2e` needs a reachable Postgres (`DATABASE_URL`) and gary-api's Python
toolchain, because it boots the real thing. It creates `gary_e2e_<random>`,
migrates it, empties it between scenarios and drops it at the end.

The stub is fast and covers almost everything, but it was written from the same
understanding that produced gary-api, so it cannot notice the two drifting
apart — that is the whole reason `test:e2e` exists. Keep it small; it is there
to catch drift, not to cover behaviour.

The specs need a Playwright browser. Either install one:

```sh
pnpm exec playwright install chromium
```

or, on a machine that already has a Chromium that Playwright did not install,
point at it directly:

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chromium pnpm test
```
