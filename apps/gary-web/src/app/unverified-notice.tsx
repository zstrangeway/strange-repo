"use client";

import { useActionState } from "react";

import { Notice as UiNotice } from "@gary/ui/components/notice";
import { SubmitButton } from "@gary/ui/components/submit-button";

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
    <UiNotice data-testid="unverified" variant="warning">
      <p>
        Your email address is not confirmed yet. Check your inbox for the link.
      </p>
      {state.error ? <p role="alert">{state.error}</p> : null}
      <form action={action}>
        <SubmitButton
          label="Send it again"
          pendingLabel="Sending…"
          pending={pending}
          variant="link"
          size="sm"
          data-testid="resend-verification"
          // Inside a Notice, so it inherits the variant's colour; the
          // underline is what marks it as something you can press.
          className="h-auto p-0 text-warning underline underline-offset-4"
        />
      </form>
    </UiNotice>
  );
}
