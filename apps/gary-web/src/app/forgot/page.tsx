import Link from "next/link";

import ForgotForm from "./form";

export const dynamic = "force-dynamic";

export default function ForgotPage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">Reset your password</h1>
      <ForgotForm />
      <Link href="/login" className="text-sm underline underline-offset-4">
        Back to sign in
      </Link>
    </main>
  );
}
