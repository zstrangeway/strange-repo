"use client";

import Link from "next/link";
import { useActionState } from "react";

import { FieldGroup } from "@gary/ui/components/field";

import { signIn, type FormState } from "../actions";
import { Field, Notice, Submit } from "../form-parts";

const RESET_DONE = "Your password has been changed, sign in with it";

export default function SignInForm({ resetDone }: { resetDone: boolean }) {
  const [state, action, pending] = useActionState<FormState, FormData>(
    signIn,
    {},
  );

  return (
    <form action={action} noValidate>
      <FieldGroup className="gap-5">
        <Notice
          error={state.error}
          confirmation={
            !state.error && resetDone ? RESET_DONE : state.confirmation
          }
        />
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
          autoComplete="current-password"
        />
        <Submit label="Sign in" pending={pending} />
        <Link
          href="/forgot"
          className="text-sm text-muted-foreground underline underline-offset-4"
        >
          Forgotten your password?
        </Link>
      </FieldGroup>
    </form>
  );
}
