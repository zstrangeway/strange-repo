# @gary/ui

The shared component library. shadcn components, vendored as source, plus the
colour tokens and dark-mode rules every app inherits.

Nothing here is built or published. Apps import the `.tsx` directly and compile
it themselves — gary-web does that via `transpilePackages` in `next.config.ts`.

## Using it from an app

```ts
import { Button } from "@gary/ui/components/button";
import { cn } from "@gary/ui/lib/utils";
```

```css
@import "@gary/ui/globals.css";
```

The CSS import is not optional. It carries the `--primary`, `--border`,
`--radius` … definitions every component references, so without it the
components render with no colour and no rounding at all.

## Adding a component

From the repository root:

```sh
pnpm dlx shadcn@latest add <name> --cwd packages/ui
```

`components.json` points the CLI at `src/components`, and its aliases match
this package's own `@gary/ui/*` paths, so generated imports resolve without
editing. Check `pnpm dlx shadcn@latest add <name> --cwd packages/ui --dry-run`
first if you want to see the files and dependencies it will add.

Some names are worth knowing before you write something yourself: `field`
covers labelled inputs with descriptions and errors, `input-group` covers
inputs with affixes, `empty` covers empty states.

## Editing a component

These files are ours — that is the whole point of shadcn. Prefer extending a
component's `cva` variants over wrapping it from outside, and leave a comment
on anything that is not upstream's. `alert.tsx` has `success` and `warning`
variants added that way; both are shaped like the stock `destructive` variant
so that re-running `add alert --overwrite` leaves an obvious diff rather than a
subtle one.

## Checks

`task typecheck` type-checks the components. There are no unit tests here on
purpose: these are presentational components with no logic of their own, and
what they render is covered end to end by gary-web's Gherkin suite.
