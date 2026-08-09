// Server-side registration hook. Next calls `register` once per server
// instance, before it handles a request.
//
// The Sentry configs live at the app root rather than beside this file,
// which is the layout Sentry documents — hence the `../`.

import * as Sentry from "@sentry/nextjs";
import type { Instrumentation } from "next";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("../sentry.server.config");
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    await import("../sentry.edge.config");
  }
}

/**
 * Every unhandled server error — Server Components, Server Actions, route
 * handlers — goes to Sentry, and to our own log on the way.
 *
 * Both, not either. Sentry is where these get triaged, but the Fly log is
 * where every other line this app writes lives, and an error that appears in
 * one and not the other makes the two accounts of the same request disagree.
 *
 * The digest is the join: in production Next replaces the message with that
 * hash before the browser sees it, so it is the only thing connecting what
 * the user was shown to what actually threw.
 */
export const onRequestError: Instrumentation.onRequestError = async (
  error,
  request,
  context,
) => {
  // Imported here rather than at the top of the file: the logger reaches for
  // node:async_hooks, which does not exist in the Edge runtime this module is
  // also bundled for.
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { getLogger } = await import("@/lib/logger");

    getLogger("server").error("server.error", {
      method: request.method,
      path: request.path,
      route: context.routePath,
      route_type: context.routeType,
      digest:
        typeof error === "object" && error !== null && "digest" in error
          ? String(error.digest)
          : undefined,
      error: error instanceof Error ? error : new Error(String(error)),
    });
  }

  return Sentry.captureRequestError(error, request, context);
};
