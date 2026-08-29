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

**scout's approval step** — [`scout-approval.feature`](scout-approval.feature).

scout was built as a tool somebody drives. The flow it is actually wanted for
is a conversation: an agent finds a posting, tailors a resume, presents it, and
submits it once a person says yes. The tailoring holds up in that world — it is
the only part an agent cannot safely do on its own, which is why scout exists —
but the *presenting* has nothing behind it, and that is the step the whole
thing turns on.

Two ideas in there worth arguing with before anything is built:

- **Approval scope and check scope are different.** A package shows everything
  about to be submitted; the check covers only the part it can honestly speak
  to; the package says which part that was. That is what makes cover letters
  and form answers safe to include without solving how to verify them.
- **Approval binds to the words, not to the posting.** Re-tailoring withdraws
  it. Without that, something regenerates the resume after approval and what
  gets sent is not what anybody said yes to.

scout still does not submit anything — the browser belongs to whatever agent is
driving, and it has the user's own logged-in sessions.

Advancement and scout's first four features came through here and have moved
into their apps with their steps.
