import Link from "next/link";
import { redirect } from "next/navigation";

import { FormCard } from "@gary/ui/components/form-card";

import { currentUser } from "@/lib/session";

import SignInForm from "./form";

export const dynamic = "force-dynamic";

export default async function LoginPage({
  searchParams,
}: PageProps<"/login">) {
  if (await currentUser()) {
    redirect("/");
  }

  const { reset } = await searchParams;

  return (
    <FormCard
      title={<h1 className="text-2xl">Sign in to gary</h1>}
      description="Enter your email and password to carry on."
      footer={
        <p>
          No account?{" "}
          <Link
            href="/signup"
            className="text-foreground underline underline-offset-4"
          >
            Sign up
          </Link>
        </p>
      }
    >
      <SignInForm resetDone={reset === "1"} />
    </FormCard>
  );
}
