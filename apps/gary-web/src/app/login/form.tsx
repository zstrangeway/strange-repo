"use client";

import Link from "next/link";
import { useActionState } from "react";

import { signIn, type FormState } from "../actions";
import { Field, Notice, Submit } from "../form-parts";

const RESET_DONE = "Your password has been changed, sign in with it";

export default function SignInForm({ resetDone }: { resetDone: boolean }) {
  const [state, action, pending] = useActionState<FormState, FormData>(
    signIn,
    {},
  );

  return (
    <form action={action} noValidate className="flex flex-col gap-4">
      <Notice
        error={state.error}
        confirmation={
          !state.error && resetDone ? RESET_DONE : state.confirmation
        }
      />
      <Field label="Email" name="email" type="email" autoComplete="username" />
      <Field
        label="Password"
        name="password"
        type="password"
        autoComplete="current-password"
      />
      <Submit label="Sign in" pending={pending} />
      <Link
        href="/forgot"
        className="text-sm text-black/60 underline underline-offset-4 dark:text-white/60"
      >
        Forgotten your password?
      </Link>
    </form>
  );
}
