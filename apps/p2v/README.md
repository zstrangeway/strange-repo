# P2V Basketball Academy

The existing P2V · Path 2 Victory website, imported from ChatGPT Sites version 7.
The HTML, CSS, JavaScript, images, and font in `dist/` are the editable source;
this is a buildless static site, so `dist/` is intentionally tracked.

## Run locally

From the repository root:

```sh
pnpm --filter p2v dev
```

Open http://localhost:8080. Node, Python 3.9+, and Task are required for the
checks; the local server uses Python. Run `pnpm install` at the repository root
to install the workspace tools. No app-specific dependencies or build step are
needed. Serve `dist/` as the web root because the site uses root-relative URLs.

## Check

```sh
pnpm --filter p2v test
```

This checks JavaScript syntax and verifies that local HTML and CSS references
resolve to files. It does not test browser interactions or external links.

## Hosting and provenance

- Current site: https://p2v-academy-refresh.blithebowl5.chatgpt.site
- Sites project: `appgprj_6acaa917b31481919fc13d3f25aa9142`
- Imported source commit: `5b711fc21b4f145aea13b0dda0d22a4607d158b2`
- `.openai/hosting.json` retains the existing Site identity and `dist` web root.

This import preserves the existing redesign, including placeholder imagery and
its `noindex,nofollow` metadata. The inquiry form prepares an email for the
visitor to send; it has no server-side delivery service. The source contains
no hosting access controls: serving these files elsewhere does not inherit
ChatGPT Sites sign-in restrictions.

GitHub commits do not automatically update the hosted Site. Publication still
uses the existing Sites workflow and audience settings.
