import Link from "next/link";

import AuthShell from "../auth-shell";
import ForgotForm from "./form";

export const dynamic = "force-dynamic";

export default function ForgotPage() {
  return (
    <AuthShell
      title="Reset your password"
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
    </AuthShell>
  );
}
