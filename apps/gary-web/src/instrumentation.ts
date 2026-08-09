// Server-side registration hook. Next calls `register` once per server
// instance, before it handles a request.
//
// The Sentry configs live at the app root rather than beside this file,
// which is the layout Sentry documents — hence the `../`.

import * as Sentry from "@sentry/nextjs";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("../sentry.server.config");
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    await import("../sentry.edge.config");
  }
}

// Every unhandled server error — Server Components, Server Actions, route
// handlers — reaches Sentry through this. Needs @sentry/nextjs >= 8.28.0.
//
// Worth knowing: these errors do NOT currently reach the structured log in
// src/lib/logger.ts, so while the DSN is unset they are recorded nowhere but
// Next's own console output.
export const onRequestError = Sentry.captureRequestError;
