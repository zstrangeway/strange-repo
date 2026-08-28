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

**scout** — a local-first, bring-your-own-model job search assistant, proposed
as a third app. Four files, and they want reading in this order:

| | |
| --- | --- |
| [`scout-postings.feature`](scout-postings.feature) | Saving a posting, pasted or from a URL |
| [`scout-tailoring.feature`](scout-tailoring.feature) | A resume aimed at one posting, and the check that it invented nothing |
| [`scout-applications.feature`](scout-applications.feature) | Where each application got to, as an append-only log |
| [`scout-mcp.feature`](scout-mcp.feature) | The same three capabilities as MCP tools over stdio |

`scout-tailoring.feature` is the one to argue with. Everything else is
bookkeeping; that file is where the product actually is, and the scenario
about an employer nobody worked for is the one the whole thing is for.

Advancement was the first thing through here and has moved into both apps with
its steps.
