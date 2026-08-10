"use client";

import { useRouter } from "next/navigation";
import { useActionState, useEffect } from "react";

import { FieldGroup } from "@gary/ui/components/field";

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
    <form action={action} noValidate>
      <FieldGroup className="gap-4">
        <Notice error={state.error} confirmation={state.confirmation} />
        {/* The card heading already says "Display name", so the field's own
            label is there for screen readers rather than repeated on screen. */}
        <Field
          label="Display name"
          name="display_name"
          autoComplete="name"
          defaultValue={current}
          labelHidden
        />
        <Submit label="Save name" pending={pending} />
      </FieldGroup>
    </form>
  );
}

export function ChangePasswordForm() {
  const [state, action, pending] = useActionState<FormState, FormData>(
    changePassword,
    {},
  );

  return (
    <form action={action} noValidate>
      <FieldGroup className="gap-4">
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
      </FieldGroup>
    </form>
  );
}
