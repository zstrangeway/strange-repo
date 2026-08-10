"use client";

import { useActionState } from "react";

import { FieldGroup } from "@gary/ui/components/field";

import { signUp, type FormState } from "../actions";
import { Field, Notice, Submit } from "../form-parts";

export default function SignUpForm() {
  const [state, action, pending] = useActionState<FormState, FormData>(
    signUp,
    {},
  );

  return (
    <form action={action} noValidate>
      <FieldGroup className="gap-5">
        <Notice error={state.error} confirmation={state.confirmation} />
        <Field label="Display name" name="display_name" autoComplete="name" />
        <Field
          label="Email"
          name="email"
          type="email"
          autoComplete="username"
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
        />
        <Submit label="Sign up" pending={pending} />
      </FieldGroup>
    </form>
  );
}
