import * as React from "react"

import { Alert, AlertDescription } from "@gary/ui/components/alert"

// Not a shadcn registry component. An Alert carrying one line of prose and
// nothing else — no title, no icon — which is what a form's error and
// confirmation messages are.
//
// The single AlertDescription is deliberate as well as tidy: the text of this
// element is what a caller's tests will read, and a title would silently
// prepend itself to every one of those assertions.

function Notice({
  children,
  ...props
}: React.ComponentProps<typeof Alert>) {
  return (
    <Alert {...props}>
      <AlertDescription>{children}</AlertDescription>
    </Alert>
  )
}

export { Notice }
