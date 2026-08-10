import type { ReactNode } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@gary/ui/components/card";

// The frame every signed-out page shares. Extracted when the fifth copy of it
// appeared, not before.
export default function AuthShell({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    // bg-muted rather than the page default: a bg-card card on a bg-background
    // page is white on white, with only the border to say where it ends.
    <main className="flex min-h-screen w-full flex-col items-center justify-center bg-muted p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          {/* CardTitle renders a div, and each of these pages is the whole
              page — so the heading element goes inside it rather than leaving
              the document with no h1. */}
          <CardTitle>
            <h1 className="text-2xl">{title}</h1>
          </CardTitle>
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
  );
}
