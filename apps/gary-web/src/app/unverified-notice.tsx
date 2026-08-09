"use client";

import { useActionState } from "react";

import { resendVerification, type FormState } from "./actions";
import { Notice } from "./form-parts";

export default function UnverifiedNotice() {
  const [state, action, pending] = useActionState<FormState, FormData>(
    resendVerification,
    {},
  );

  // Once the resend lands, the confirmation replaces the nag rather than
  // sitting under it — two boxes saying different things is worse than one.
  if (state.confirmation && !state.error) {
    return <Notice confirmation={state.confirmation} />;
  }

  return (
    <div
      data-testid="unverified"
      className="flex flex-col items-center gap-2 rounded bg-amber-100 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200"
    >
      <p>Your email address is not confirmed yet. Check your inbox for the link.</p>
      {state.error ? <p role="alert">{state.error}</p> : null}
      <form action={action}>
        <button
          type="submit"
          disabled={pending}
          data-testid="resend-verification"
          className="underline underline-offset-4 disabled:opacity-50"
        >
          {pending ? "Sending…" : "Send it again"}
        </button>
      </form>
    </div>
  );
}
