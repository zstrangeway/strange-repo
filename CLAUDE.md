# CLAUDE.md

## This file

Keep it bare. It holds only course-correcting adjustments to default behavior —
things that would otherwise be gotten wrong. No project overview, no architecture
notes, no restating of general good practice.

## New projects

Scaffold with the official CLI rather than hand-writing boilerplate.
Preferred stacks: Next.js for web, FastAPI for services, Postgres via
SQLAlchemy and Alembic for data.

Use pnpm, never npm — for installs, scripts, and scaffolding alike.

## New features

Drive the work with BDD. Write the `.feature` specs first and review them with
me — get agreement on the functionality before writing any implementation code.
The runner follows the language: `behave` for Python, `@cucumber/cucumber`
driving a real browser through Playwright for web apps.

Ship every new feature at 100% test coverage. A new app is different: a bare
scaffold has no behavior to cover, so don't wire up the coverage gate until the
first real feature lands.

## Dependencies

Check what the project already pulls in before reaching for something new — an
existing dependency usually covers it. If nothing does, bring me the options and
discuss before adding anything.

## Commands

Every app gets a `Taskfile.yml`, and its `package.json` scripts delegate to it,
so `pnpm test` means the same thing in every app.

## Deploys

Fly.io, deployed by GitHub Actions on pushes to main. Keep deploys gated behind
the test and image-build jobs; don't move them to a platform integration that
ships whatever landed.

## Work you can't verify

If you can't test a change, say so and say what would let you — don't ship it
as a guess and let the next deploy find out. That has cost more time than
asking ever would.

Say when behavior won't show up where I'd look for it: a fetch that runs on the
server never appears in browser devtools, and I'll waste an hour there.

A check or setup step that silently does nothing is worse than none. Make them
report what they did.
