"use client";

import { useActionState } from "react";

import { requestPasswordReset, type FormState } from "../actions";
import { Field, Notice, Submit } from "../form-parts";

export default function ForgotForm() {
  const [state, action, pending] = useActionState<FormState, FormData>(
    requestPasswordReset,
    {},
  );

  return (
    <form action={action} noValidate className="flex flex-col gap-4">
      <Notice error={state.error} confirmation={state.confirmation} />
      <Field label="Email" name="email" type="email" autoComplete="username" />
      <Submit label="Send me a link" pending={pending} />
    </form>
  );
}
