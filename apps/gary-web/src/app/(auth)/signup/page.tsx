import Link from "next/link";
import { redirect } from "next/navigation";

import { FormCard } from "@gary/ui/components/form-card";

import { currentUser } from "@/lib/session";

import SignUpForm from "./form";

export const dynamic = "force-dynamic";

export default async function SignUpPage() {
  if (await currentUser()) {
    redirect("/");
  }

  return (
    <FormCard
      title={<h1 className="text-2xl">Create an account</h1>}
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
    </FormCard>
  );
}
