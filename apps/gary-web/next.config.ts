import path from "node:path";
import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Bundle a self-contained server for the container image.
  output: "standalone",
  // Trace from the workspace root so pnpm-linked dependencies are included.
  outputFileTracingRoot: path.join(import.meta.dirname, "../.."),
};

// org and project are deliberately not set here — they come from SENTRY_ORG
// and SENTRY_PROJECT, which the plugin reads itself. Nothing about this
// repository should have to change when the Sentry account exists.
export default withSentryConfig(nextConfig, {
  // Source map upload. Skipped when SENTRY_AUTH_TOKEN is absent, which is
  // every build until the token is a CI secret — the build still succeeds,
  // production stack traces are just minified until then.
  authToken: process.env.SENTRY_AUTH_TOKEN,
  widenClientFileUpload: true,

  // Events go out through gary-web's own origin instead of sentry.io, so an
  // ad blocker cannot quietly drop them.
  tunnelRoute: "/monitoring",

  // Never silent. This was `!process.env.CI`, which was wrong in the one place
  // it mattered: `flyctl deploy --remote-only` builds on Fly's builder, not on
  // the GitHub runner, so CI is unset there and the plugin went quiet during
  // the only build that actually uploads. The first real deploy printed the
  // Dockerfile's "uploading source maps" line and then nothing at all, which
  // is indistinguishable from an upload that silently failed.
  silent: false,
});
