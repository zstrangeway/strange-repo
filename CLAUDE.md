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

## Bugs

Every bug gets a test before it gets a fix. Write the test, watch it fail for
the reason you think it fails, then fix it and watch it pass. A fix you never
saw fail is a guess that happens to be green.

## UI components

Never hand-write one. Work down this list and stop at the first hit:

1. `packages/ui/src/components` — take what is there. "Close enough with a new
   variant" counts as a hit; add the variant to that component's `cva` rather
   than starting something new beside it.
2. The shadcn registry —
   `pnpm dlx shadcn@latest add <name> --cwd packages/ui` from the repo root.
   Search it properly before deciding it has nothing: `field`, `input-group`
   and `empty` all cover things people reach for a bespoke component to do.
3. Only with both exhausted, write one — into `packages/ui`, built from the
   primitives already there, and say in your summary that you had to.

Vendored shadcn files are ours to edit; that is what shadcn is for. Comment
anything that is not upstream's, so the next `add --overwrite` shows an honest
diff.

## Dependencies

Check what the project already pulls in before reaching for something new — an
existing dependency usually covers it. If nothing does, bring me the options and
discuss before adding anything.

## Model spend

OpenRouter is my money. The budget is about $50 a day of Sonnet 5 — enough to
work with, not enough to be careless with.

Anything run by hand — a smoke check, seeing whether a prompt change took —
names a `:free` model. They cost nothing and exercise the same path, and one
already caught a model skipping a tool. Reach for a paid model only when the
question is about that model.

Where a paid model is the default, it is Sonnet 5. Don't reach for the most
capable thing available as a starting point; reach for it when something has
shown it needs one.

Before a run that will cost more than a few cents, say what you expect it to
cost and wait. Afterwards, say what it did cost — the number is already
printed, so passing it on is free.

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
