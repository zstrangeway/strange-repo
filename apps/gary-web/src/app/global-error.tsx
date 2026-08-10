"use client";

// The last boundary: catches what the root layout throws, and React render
// errors that nothing below caught. It replaces the root layout when active,
// so it has to bring its own <html> and <body> — and its own stylesheet, for
// the same reason: the layout's import goes with the layout.
//
// Not built from Sentry's template, which renders `next/error`'s default
// export — this version of Next declares that export Pages Router only. The
// props are this version's too: it hands the boundary `retry`, where older
// Next passed `reset`.

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

import { Button } from "@gary/ui/components/button";

import "./globals.css";

export default function GlobalError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col items-center justify-center gap-6 p-6 font-sans">
        <h2 className="text-2xl font-semibold tracking-tight">
          Something went wrong
        </h2>
        <Button type="button" variant="outline" onClick={() => retry()}>
          Try again
        </Button>
      </body>
    </html>
  );
}
