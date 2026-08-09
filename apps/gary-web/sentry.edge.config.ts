// Sentry, Edge runtime. Loaded by src/instrumentation.ts.
//
// gary-web runs no edge code today — there is no middleware and no edge
// route handler. This is here so that the day someone adds one, its errors
// are not silently unreported.

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN,

  // Same reasoning as the other two runtimes: omitted rather than empty.
  sendDefaultPii: false,

  tracesSampleRate: process.env.NODE_ENV === "development" ? 1.0 : 0.1,
});
