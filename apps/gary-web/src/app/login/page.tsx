import Link from "next/link";
import { redirect } from "next/navigation";

import { currentUser } from "@/lib/session";

import AuthShell from "../auth-shell";
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
    <AuthShell
      title="Sign in to gary"
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
    </AuthShell>
  );
}
