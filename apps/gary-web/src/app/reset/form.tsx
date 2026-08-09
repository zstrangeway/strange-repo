"use client";

import { useActionState } from "react";

import { confirmPasswordReset, type FormState } from "../actions";
import { Field, Notice, Submit } from "../form-parts";

export default function ResetForm({ token }: { token: string }) {
  const [state, action, pending] = useActionState<FormState, FormData>(
    confirmPasswordReset,
    {},
  );

  return (
    <form action={action} noValidate className="flex flex-col gap-4">
      <Notice error={state.error} confirmation={state.confirmation} />
      <input type="hidden" name="token" value={token} />
      <Field
        label="New password"
        name="new_password"
        type="password"
        autoComplete="new-password"
      />
      <Submit label="Set password" pending={pending} />
    </form>
  );
}
