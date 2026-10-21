# P2V Basketball Academy

P2V · Path 2 Victory, migrated from the existing ChatGPT Site to React with
Next.js and TypeScript. The site still exports ordinary static files; it does
not require a Node server in production.

## Development

Use Node 24+, pnpm 10, and Python 3.9+. Install from the repository root:

```sh
pnpm install --frozen-lockfile
pnpm --filter p2v dev
```

Open http://127.0.0.1:8080. Next serves the React application with hot reload.
The existing `/training.html`, `/teams.html`, `/facility.html`, `/about.html`,
`/schedule.html`, and `/contact.html` links work in development and in the
static export.

## Source and build

- `src/app/`: the seven pages, page metadata, shared layout, and original CSS.
- `src/components/`: the header, footer, repeated content sections, and the
  interactive training tabs and inquiry form. Interactive controls use React
  state and reuse the workspace UI button, input, label, and textarea.
- `public/assets/`: the original images, SVGs, and local Barlow font.
- `out/`: generated static export; ignored by Git.

The original P2V CSS styles the shared controls; the gary theme and Tailwind
stylesheet are not imported. The appearance, copy, mobile navigation, keyboard
tab controls, query-string inquiry interests, and email preview are preserved.

```sh
pnpm --filter p2v build
pnpm --filter p2v serve
```

The production export is served at http://127.0.0.1:8080. Deploy `out/` as the
web root. Each page is prerendered to HTML, including the original `.html`
addresses; hydration enables its React interactions. Images and the font are
local, so builds do not fetch fonts or content from external services.

## Verification

```sh
pnpm --filter p2v exec playwright install chromium
pnpm --filter p2v test
pnpm --filter p2v typecheck
```

`test` builds and type-checks the application, validates local HTML and CSS
references in the export, then runs the Cucumber scenarios in a real Chromium
browser against those production files. The scenarios cover all seven existing
pages, loaded images, mobile layout and menu, training-tab keyboard navigation,
inquiry preselection, validation, email encoding, editing, copying (including a
denied clipboard), FAQs, and browser runtime errors. They also passed against
the original static site before migration. CI installs Chromium with its Linux
dependencies and runs the same test command.

To use a locally installed Chromium instead of Playwright's downloaded one:

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium pnpm --filter p2v test
```

External links and delivery through a visitor's email application are not
automated. The inquiry form prepares an email for the visitor to send; there
is no server-side submission service.

## Hosting and provenance

- Current hosted site: https://p2v-academy-refresh.blithebowl5.chatgpt.site
- Sites project: `appgprj_6acaa917b31481919fc13d3f25aa9142`
- Original imported version: 7, source commit
  `5b711fc21b4f145aea13b0dda0d22a4607d158b2`.
- `.openai/hosting.json` retains that Site identity and points to `out/`.

This migration retains the existing placeholder imagery and `noindex,nofollow`
metadata. GitHub pushes do not deploy the Site. Publishing remains a separate
Sites operation with the existing audience settings. Those access controls
belong to Sites and are not embedded in the static export.
