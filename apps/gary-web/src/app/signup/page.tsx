import Link from "next/link";
import { redirect } from "next/navigation";

import { currentUser } from "@/lib/session";

import SignUpForm from "./form";

export const dynamic = "force-dynamic";

export default async function SignUpPage() {
  if (await currentUser()) {
    redirect("/");
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">Create an account</h1>
      <SignUpForm />
      <p className="text-sm text-black/60 dark:text-white/60">
        Already have one?{" "}
        <Link href="/login" className="underline underline-offset-4">
          Sign in
        </Link>
      </p>
    </main>
  );
}
