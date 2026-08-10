import Link from "next/link";

import { FormCard } from "@gary/ui/components/form-card";

import { verifyEmail } from "../../actions";
import { Notice } from "../../form-parts";

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
    <FormCard
      title={<h1 className="text-2xl">Confirm your address</h1>}
      footer={
        <Link href="/" className="text-foreground underline underline-offset-4">
          Go home
        </Link>
      }
    >
      <Notice
        error={result.error}
        confirmation="Thank you — your email address is confirmed."
      />
    </FormCard>
  );
}
