"use client";

import { useActionState } from "react";

import { FieldGroup } from "@gary/ui/components/field";
import { SubmitButton } from "@gary/ui/components/submit-button";

import { confirmPasswordReset, type FormState } from "../actions";
import { Field, Notice } from "../form-parts";

export default function ResetForm({ token }: { token: string }) {
  const [state, action, pending] = useActionState<FormState, FormData>(
    confirmPasswordReset,
    {},
  );

  return (
    <form action={action} noValidate>
      <FieldGroup className="gap-5">
        <Notice error={state.error} confirmation={state.confirmation} />
        <input type="hidden" name="token" value={token} />
        <Field
          label="New password"
          name="new_password"
          type="password"
          autoComplete="new-password"
        />
        <SubmitButton label="Set password" pending={pending} />
      </FieldGroup>
    </form>
  );
}
