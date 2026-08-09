// Sentry, Node.js server runtime. Loaded by src/instrumentation.ts.
//
// This is the runtime that renders Server Components and runs Server
// Actions, so it is the one that sees passwords and session tokens. Read the
// two omissions below before adding anything to this file.

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN,

  // No `dataCollection` block, on purpose — passing it, even empty, opts
  // every unset category into its permissive default. See the note in
  // src/instrumentation-client.ts.
  sendDefaultPii: false,

  // `includeLocalVariables: true` is in Sentry's template and is left out
  // here on purpose. It attaches the *values* of local variables to stack
  // frames, and the locals in this app's Server Actions include `password`,
  // `current_password` and `new_password`. A crash in signIn would post a
  // plaintext password to a third party.

  tracesSampleRate: process.env.NODE_ENV === "development" ? 1.0 : 0.1,
});
