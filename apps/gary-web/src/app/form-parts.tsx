"use client";

import { useId } from "react";

import { Alert, AlertDescription } from "@gary/ui/components/alert";
import { Button } from "@gary/ui/components/button";
import { Field as FieldRoot, FieldLabel } from "@gary/ui/components/field";
import { Input } from "@gary/ui/components/input";

// gary-web's own compositions, built from @gary/ui's shadcn primitives. What
// lives here rather than in the library is the part the specs bind to — the
// data-testid contract — and nothing else.

export function Field({
  label,
  name,
  type = "text",
  autoComplete,
  defaultValue,
  labelHidden = false,
}: {
  label: string;
  name: string;
  type?: string;
  autoComplete?: string;
  defaultValue?: string;
  labelHidden?: boolean;
}) {
  const id = useId();

  return (
    <FieldRoot>
      <FieldLabel htmlFor={id} className={labelHidden ? "sr-only" : undefined}>
        {label}
      </FieldLabel>
      <Input
        id={id}
        name={name}
        type={type}
        autoComplete={autoComplete}
        defaultValue={defaultValue}
        data-testid={`field-${name}`}
      />
    </FieldRoot>
  );
}

export function Submit({ label, pending }: { label: string; pending: boolean }) {
  return (
    <Button type="submit" disabled={pending}>
      {pending ? "Working…" : label}
    </Button>
  );
}

export function Notice({ error, confirmation }: { error?: string; confirmation?: string }) {
  if (error) {
    return (
      <Alert data-testid="error" variant="destructive">
        {/* The description carries the message and nothing else: a spec reads
            this element's whole text and compares it to the expected string,
            so an AlertTitle above it would be silently prepended to every
            assertion. */}
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (confirmation) {
    return (
      // role overrides Alert's own "alert": a confirmation is not urgent, and
      // role="status" is what announces it without interrupting.
      <Alert data-testid="confirmation" role="status" variant="success">
        <AlertDescription>{confirmation}</AlertDescription>
      </Alert>
    );
  }

  return null;
}
