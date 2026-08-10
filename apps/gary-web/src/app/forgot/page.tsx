import Link from "next/link";

import { FormCard } from "@gary/ui/components/form-card";

import ForgotForm from "./form";

export const dynamic = "force-dynamic";

export default function ForgotPage() {
  return (
    <FormCard
      title={<h1 className="text-2xl">Reset your password</h1>}
      description="We will email you a link to set a new one."
      footer={
        <Link
          href="/login"
          className="text-foreground underline underline-offset-4"
        >
          Back to sign in
        </Link>
      }
    >
      <ForgotForm />
    </FormCard>
  );
}
