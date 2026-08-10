import Link from "next/link";

import { FormCard } from "@gary/ui/components/form-card";

import { absoluteUrl } from "@/lib/urls";

import { completeSignIn } from "../../actions";
import { Notice } from "../../form-parts";

export const dynamic = "force-dynamic";

const NO_CODE = "That sign in did not complete, try again";

export default async function SignedInPage({
  searchParams,
}: PageProps<"/signed-in">) {
  const { code, state, error } = await searchParams;

  // Someone who changed their mind at the provider arrives here with an
  // error and no code. That is not a failure worth a red box — it is what
  // pressing cancel does — so it reads as an ordinary return to sign in.
  const cancelled = typeof error === "string" && error === "access_denied";

  const result =
    typeof code === "string" && typeof state === "string" && !cancelled
      ? await completeSignIn(state, code, await absoluteUrl("/signed-in"))
      : { error: cancelled ? undefined : NO_CODE };

  return (
    <FormCard
      title={<h1 className="text-2xl">Sign in to gary</h1>}
      footer={
        <Link
          href="/login"
          className="text-foreground underline underline-offset-4"
        >
          Back to sign in
        </Link>
      }
    >
      <Notice error={result.error} />
    </FormCard>
  );
}
