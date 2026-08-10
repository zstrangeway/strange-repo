import Link from "next/link";

import { callApi } from "@/lib/api";

import AuthShell from "../auth-shell";
import { Notice } from "../form-parts";
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
    <AuthShell
      title="Set a new password"
      footer={
        <Link
          href="/forgot"
          className="text-foreground underline underline-offset-4"
        >
          Ask for a new link
        </Link>
      }
    >
      {usable.ok ? <ResetForm token={value} /> : <Notice error={DEAD_LINK} />}
    </AuthShell>
  );
}
