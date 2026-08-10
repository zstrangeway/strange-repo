import Link from "next/link";
import { redirect } from "next/navigation";

import { currentUser } from "@/lib/session";

import AuthShell from "../auth-shell";
import SignUpForm from "./form";

export const dynamic = "force-dynamic";

export default async function SignUpPage() {
  if (await currentUser()) {
    redirect("/");
  }

  return (
    <AuthShell
      title="Create an account"
      description="A name, an email address, and a password is all it takes."
      footer={
        <p>
          Already have one?{" "}
          <Link
            href="/login"
            className="text-foreground underline underline-offset-4"
          >
            Sign in
          </Link>
        </p>
      }
    >
      <SignUpForm />
    </AuthShell>
  );
}
