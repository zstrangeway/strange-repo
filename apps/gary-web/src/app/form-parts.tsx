"use client";

import type { ComponentProps } from "react";

import { Notice as UiNotice } from "@gary/ui/components/notice";
import { TextField } from "@gary/ui/components/text-field";

// The only two things here are gary-web's own: the data-testid contract the
// Gherkin steps bind to, and the FormState shape the server actions return.
// There is no layout and no styling in this file on purpose — the moment
// either shows up, it belongs in @gary/ui instead.

export function Field({
  name,
  ...props
}: ComponentProps<typeof TextField> & { name: string }) {
  return <TextField name={name} data-testid={`field-${name}`} {...props} />;
}

export function Notice({
  error,
  confirmation,
}: {
  error?: string;
  confirmation?: string;
}) {
  if (error) {
    return (
      <UiNotice variant="destructive" data-testid="error">
        {error}
      </UiNotice>
    );
  }

  if (confirmation) {
    return (
      // role overrides Alert's own "alert": a confirmation is not urgent, and
      // role="status" is what announces it without interrupting.
      <UiNotice variant="success" role="status" data-testid="confirmation">
        {confirmation}
      </UiNotice>
    );
  }

  return null;
}
