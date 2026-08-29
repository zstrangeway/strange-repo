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

## The components that are not from the registry

Four of them, each written here only after the registry came up empty, and
each built from the vendored primitives rather than from raw markup:

| Component      | What it is                                                  |
| -------------- | ----------------------------------------------------------- |
| `TextField`    | `Field` + `FieldLabel` + `Input`, with a generated id wiring the label to the control |
| `SubmitButton` | A submit `Button` that disables itself and changes its label while a form is in flight |
| `Notice`       | An `Alert` holding one line of prose — no title, no icon    |
| `FormCard`     | A `Card` holding a single form, centred on its own page      |
| `ThemeProvider` | Light/dark/system in localStorage, applied to `<html>`. Exports `useTheme`. The part of next-themes worth having, without the dependency |

They spread their remaining props onto the element a caller would expect, so
app-specific attributes — `data-testid`, `name`, `autoComplete` — pass
straight through. That is the seam: nothing in this package should know an
app's test selectors or its form-state shape.

## Editing a component

These files are ours — that is the whole point of shadcn. Prefer extending a
component's `cva` variants over wrapping it from outside, and leave a comment
on anything that is not upstream's. `alert.tsx` has `success` and `warning`
variants added that way; both are shaped like the stock `destructive` variant
so that re-running `add alert --overwrite` leaves an obvious diff rather than a
subtle one.

## Checks

`pnpm --filter @gary/ui test` lints and type-checks the components, and CI runs
it as its own job that deploys wait on. There are no unit tests here on
purpose: these are presentational components with no logic of their own, and
what they render is covered end to end by gary-web's Gherkin suite.

The eslint config is the workspace root's `eslint.config.mjs`, not one in here,
and the lint task runs from the root — eslint will not lint a file outside its
config's base path, and run from anywhere below the root it answered "File
ignored because outside of base path" for every file in this package. As a
*warning*, so it exited 0 having linted nothing. These components went unlinted
that way for as long as the package has existed.

The root config gives this package the TypeScript rules and not the Next ones.
A component library has no routing, no `next/image` and no server boundary for
those to have an opinion about.
