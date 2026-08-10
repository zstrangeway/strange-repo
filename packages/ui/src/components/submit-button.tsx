"use client"

// Not a shadcn registry component. Every form here submits through a server
// action and has to say so while it is in flight.

import * as React from "react"

import { Button } from "@gary/ui/components/button"

function SubmitButton({
  label,
  pending = false,
  pendingLabel = "Working…",
  ...props
}: Omit<React.ComponentProps<typeof Button>, "children"> & {
  label: string
  pending?: boolean
  pendingLabel?: string
}) {
  return (
    // disabled after the spread: a caller may disable this for its own
    // reasons, but nothing may re-enable it mid-submit.
    <Button type="submit" {...props} disabled={pending || props.disabled}>
      {pending ? pendingLabel : label}
    </Button>
  )
}

export { SubmitButton }
