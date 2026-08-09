// Sentry, browser runtime. Loaded by Next automatically — this file is a
// convention, not something imported from anywhere.
//
// Errors and tracing only. Session replay, logs, profiling and metrics are
// deliberately not here: Sentry's own guidance is that the baseline install
// is errors + tracing, and that wiring the rest up before anyone has asked
// for it is over-instrumenting.

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  // Unset until there is an account. The SDK no-ops without a DSN rather
  // than throwing, so this ships inert and switches on with one secret.
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // There is deliberately no `dataCollection` block here. Sentry's reference
  // is explicit that passing that object — *even empty* — flips every unset
  // category to its permissive default, and the template ships it as an
  // empty object full of commented-out opt-outs. Omitting it falls back to
  // sendDefaultPii instead, which is what we want: gary_session holds a live
  // gary-api bearer token, and the sign-in, sign-up, reset and change-password
  // forms all carry passwords.
  sendDefaultPii: false,

  // Everything in development, a tenth of it in production.
  tracesSampleRate: process.env.NODE_ENV === "development" ? 1.0 : 0.1,
});

// App Router navigations become spans. Without this, client-side route
// changes are invisible and only the first load is traced.
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
