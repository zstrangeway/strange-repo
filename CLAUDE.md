# CLAUDE.md

## This file

Keep it bare. It holds only course-correcting adjustments to default behavior —
things that would otherwise be gotten wrong. No project overview, no architecture
notes, no restating of general good practice.

## New projects

Scaffold with the official CLI rather than hand-writing boilerplate.
Preferred stacks: Next.js for web, FastAPI for services.

Use pnpm, never npm — for installs, scripts, and scaffolding alike.

## New features

Drive the work with BDD, using `behave` as the Gherkin runner. Write the
`.feature` specs first and review them with me — get agreement on the
functionality before writing any implementation code.

Ship every new feature at 100% test coverage. A new app is different: a bare
scaffold has no behavior to cover, so don't wire up the coverage gate until the
first real feature lands.

## Dependencies

Check what the project already pulls in before reaching for something new — an
existing dependency usually covers it. If nothing does, bring me the options and
discuss before adding anything.
