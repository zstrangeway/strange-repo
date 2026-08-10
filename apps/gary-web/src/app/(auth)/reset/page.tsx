import Link from "next/link";

import { FormCard } from "@gary/ui/components/form-card";

import { callApi } from "@/lib/api";

import { Notice } from "../../form-parts";
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
    <FormCard
      title={<h1 className="text-2xl">Set a new password</h1>}
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
    </FormCard>
  );
}
