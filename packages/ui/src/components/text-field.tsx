"use client"

// Not a shadcn registry component. A labelled text input is the shape every
// form in this repo actually reaches for, and composing Field + FieldLabel +
// Input by hand at each call site is how the three drift apart.

import * as React from "react"

import { Field, FieldLabel } from "@gary/ui/components/field"
import { Input } from "@gary/ui/components/input"

function TextField({
  label,
  labelHidden = false,
  id,
  ...props
}: React.ComponentProps<typeof Input> & {
  label: string
  /** Keeps the label for screen readers when a heading already names the field. */
  labelHidden?: boolean
}) {
  // Only used when the caller has no id of its own — the label needs
  // something to point at, and a wrong htmlFor is worse than none.
  const generatedId = React.useId()
  const inputId = id ?? generatedId

  return (
    <Field>
      <FieldLabel
        htmlFor={inputId}
        className={labelHidden ? "sr-only" : undefined}
      >
        {label}
      </FieldLabel>
      <Input id={inputId} {...props} />
    </Field>
  )
}

export { TextField }
