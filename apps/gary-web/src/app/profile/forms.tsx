"use client";

import { useRouter } from "next/navigation";
import { useActionState, useEffect } from "react";

import { changePassword, updateDisplayName, type FormState } from "../actions";
import { Field, Notice, Submit } from "../form-parts";

export function DisplayNameForm({ current }: { current: string }) {
  const [state, action, pending] = useActionState<FormState, FormData>(
    updateDisplayName,
    {},
  );
  const router = useRouter();

  useEffect(() => {
    // The name is rendered on the server, here and on the home page, so the
    // route has to be refetched or the old one stays on screen.
    if (state.confirmation) {
      router.refresh();
    }
  }, [state.confirmation, router]);

  return (
    <form action={action} noValidate className="flex flex-col gap-3">
      <h2 className="text-sm font-medium">Display name</h2>
      <Notice error={state.error} confirmation={state.confirmation} />
      <label className="flex flex-col gap-1 text-sm">
        <span className="sr-only">Display name</span>
        <input
          name="display_name"
          defaultValue={current}
          data-testid="field-display_name"
          className="rounded border border-black/15 bg-transparent px-3 py-2 text-base dark:border-white/20"
        />
      </label>
      <Submit label="Save name" pending={pending} />
    </form>
  );
}

export function ChangePasswordForm() {
  const [state, action, pending] = useActionState<FormState, FormData>(
    changePassword,
    {},
  );

  return (
    <form action={action} noValidate className="flex flex-col gap-3">
      <h2 className="text-sm font-medium">Password</h2>
      <Notice error={state.error} confirmation={state.confirmation} />
      <Field
        label="Current password"
        name="current_password"
        type="password"
        autoComplete="current-password"
      />
      <Field
        label="New password"
        name="new_password"
        type="password"
        autoComplete="new-password"
      />
      <Submit label="Change password" pending={pending} />
    </form>
  );
}
