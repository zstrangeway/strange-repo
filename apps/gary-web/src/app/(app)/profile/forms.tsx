"use client";

import { useState, useTransition } from "react";

import { FieldGroup } from "@gary/ui/components/field";
import { SubmitButton } from "@gary/ui/components/submit-button";

import { updateDisplayName, type Outcome } from "@/lib/gary";
import { useSession } from "@/lib/use-session";

import { Field, Notice } from "../../form-parts";

export function DisplayNameForm({ current }: { current: string }) {
  const [outcome, setOutcome] = useState<Outcome>({});
  const [pending, start] = useTransition();
  const { reload } = useSession();

  return (
    <form
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        const name = new FormData(event.currentTarget).get("display_name");
        start(async () => {
          const result = await updateDisplayName(
            typeof name === "string" ? name : "",
          );
          setOutcome(result);
          // The name is shown in the sidebar and on the home page too, so the
          // session is re-read rather than only this form updating.
          if (result.confirmation) {
            await reload();
          }
        });
      }}
    >
      <FieldGroup className="gap-4">
        <Notice error={outcome.error} confirmation={outcome.confirmation} />
        {/* The card heading already says "Display name", so the field's own
            label is there for screen readers rather than repeated on screen. */}
        <Field
          label="Display name"
          name="display_name"
          autoComplete="name"
          defaultValue={current}
          labelHidden
        />
        <SubmitButton label="Save name" pending={pending} />
      </FieldGroup>
    </form>
  );
}
