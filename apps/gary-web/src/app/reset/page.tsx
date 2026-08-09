import Link from "next/link";

import { callApi } from "@/lib/api";

import ResetForm from "./form";

export const dynamic = "force-dynamic";

const DEAD_LINK = "That reset link has expired or has already been used";

export default async function ResetPage({ searchParams }: PageProps<"/reset">) {
  const { token } = await searchParams;
  const value = typeof token === "string" ? token : "";

  // Checked on open rather than on submit: being told the link is dead after
  // typing a new password twice is a worse way to find out.
  const usable = value
    ? await callApi(`/auth/password-reset/${encodeURIComponent(value)}`)
    : ({ ok: false } as const);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">Set a new password</h1>

      {usable.ok ? (
        <ResetForm token={value} />
      ) : (
        <p
          data-testid="error"
          role="alert"
          className="rounded bg-red-100 px-3 py-2 text-sm text-red-800 dark:bg-red-950 dark:text-red-300"
        >
          {DEAD_LINK}
        </p>
      )}

      <Link href="/forgot" className="text-sm underline underline-offset-4">
        Ask for a new link
      </Link>
    </main>
  );
}
