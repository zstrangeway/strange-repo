import Link from "next/link";
import { redirect } from "next/navigation";

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
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">Sign in to gary</h1>
      <SignInForm resetDone={reset === "1"} />
      <p className="text-sm text-black/60 dark:text-white/60">
        No account?{" "}
        <Link href="/signup" className="underline underline-offset-4">
          Sign up
        </Link>
      </p>
    </main>
  );
}
