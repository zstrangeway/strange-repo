# Proposals

Gherkin written for review, before anything implements it. Per `CLAUDE.md` the
specs come first and get agreed before implementation code exists — this is
where they wait in the meantime.

**They are here rather than in an app's `features/` because both runners walk
those trees and fail on an undefined step.** behave exits 1, cucumber-js exits
1, `pnpm test` goes red and the deploy gate holds everything back. That has
already happened once: `41af12c` pulled the roll specs back out for exactly
this reason, having learnt it the hard way.

So a proposal moves in the other direction when it is agreed: the `.feature`
file goes to `apps/<app>/features/`, its steps are written alongside, and the
copy here is deleted. Nothing should live in both places.

A proposal that is rejected is deleted too. This directory is a queue, not an
archive — git remembers what was thought about and decided against, and a
folder of things nobody is going to build reads like a roadmap.

## Waiting

| Proposal | For | What it decides |
| --- | --- | --- |
| [`advancement/`](advancement) | gary-api, gary-web | Whether experience is gary's to award, and levels the engine's to grant |
