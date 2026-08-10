"use client";

import { useActionState } from "react";

import { FieldGroup } from "@gary/ui/components/field";

import { requestPasswordReset, type FormState } from "../actions";
import { Field, Notice, Submit } from "../form-parts";

export default function ForgotForm() {
  const [state, action, pending] = useActionState<FormState, FormData>(
    requestPasswordReset,
    {},
  );

  return (
    <form action={action} noValidate>
      <FieldGroup className="gap-5">
        <Notice error={state.error} confirmation={state.confirmation} />
        <Field
          label="Email"
          name="email"
          type="email"
          autoComplete="username"
        />
        <Submit label="Send me a link" pending={pending} />
      </FieldGroup>
    </form>
  );
}
