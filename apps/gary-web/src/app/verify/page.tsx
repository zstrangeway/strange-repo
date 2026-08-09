import Link from "next/link";

import { verifyEmail } from "../actions";

export const dynamic = "force-dynamic";

const DEAD_LINK = "That verification link has expired or has already been used";

export default async function VerifyPage({ searchParams }: PageProps<"/verify">) {
  const { token } = await searchParams;
  const value = typeof token === "string" ? token : "";

  // Verified on open rather than behind a button: the person clicked a link
  // in their own email, which is the confirmation. Asking them to confirm
  // the confirmation is a step for nobody's benefit.
  //
  // Deliberately no session required — the email is often opened on a device
  // that has never signed in.
  const result = value ? await verifyEmail(value) : { error: DEAD_LINK };

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">Confirm your address</h1>

      {result.error ? (
        <p
          data-testid="error"
          role="alert"
          className="rounded bg-red-100 px-3 py-2 text-sm text-red-800 dark:bg-red-950 dark:text-red-300"
        >
          {result.error}
        </p>
      ) : (
        <p
          data-testid="confirmation"
          role="status"
          className="rounded bg-green-100 px-3 py-2 text-sm text-green-800 dark:bg-green-950 dark:text-green-300"
        >
          Thank you — your email address is confirmed.
        </p>
      )}

      <Link href="/" className="text-sm underline underline-offset-4">
        Go home
      </Link>
    </main>
  );
}
