import * as React from "react"

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@gary/ui/components/card"
import { cn } from "@gary/ui/lib/utils"

// Not a shadcn registry component. A card holding a single form, centred on
// its own page — sign in, sign up, reset a password.
//
// It renders the page's <main> landmark, because that is what these pages
// are: one form and nothing else. Two of these on one page would be two
// mains, so don't.

function FormCard({
  title,
  description,
  footer,
  children,
  className,
  ...props
}: Omit<React.ComponentProps<typeof Card>, "title"> & {
  /** Takes a node rather than a string: the heading level belongs to the page. */
  title: React.ReactNode
  description?: React.ReactNode
  footer?: React.ReactNode
}) {
  return (
    // bg-muted rather than the page default: a bg-card card on a bg-background
    // page is white on white, with only the border to say where it ends.
    <main className="flex min-h-screen w-full flex-col items-center justify-center bg-muted p-6">
      <Card className={cn("w-full max-w-sm", className)} {...props}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </CardHeader>
        <CardContent>{children}</CardContent>
        {footer ? (
          <CardFooter className="text-sm text-muted-foreground">
            {footer}
          </CardFooter>
        ) : null}
      </Card>
    </main>
  )
}

export { FormCard }
