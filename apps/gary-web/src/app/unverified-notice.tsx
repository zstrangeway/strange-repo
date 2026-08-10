"use client";

import { useActionState } from "react";

import { Alert, AlertDescription } from "@gary/ui/components/alert";
import { Button } from "@gary/ui/components/button";

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
    <Alert data-testid="unverified" variant="warning">
      <AlertDescription>
        <p>
          Your email address is not confirmed yet. Check your inbox for the
          link.
        </p>
        {state.error ? <p role="alert">{state.error}</p> : null}
        <form action={action}>
          <Button
            type="submit"
            variant="link"
            size="sm"
            disabled={pending}
            data-testid="resend-verification"
            // Inside an Alert, so it inherits the variant's colour; the
            // underline is what marks it as something you can press.
            className="h-auto p-0 text-warning underline underline-offset-4"
          >
            {pending ? "Sending…" : "Send it again"}
          </Button>
        </form>
      </AlertDescription>
    </Alert>
  );
}
