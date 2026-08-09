import Link from "next/link";
import { redirect } from "next/navigation";

import { currentUser } from "@/lib/session";

import { signOut } from "../actions";
import { ChangePasswordForm, DisplayNameForm } from "./forms";

export const dynamic = "force-dynamic";

export default async function ProfilePage() {
  const user = await currentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center gap-8 p-8">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Your profile</h1>
        <p data-testid="profile-email" className="font-mono text-sm text-black/60 dark:text-white/60">
          {user.email}
        </p>
      </div>

      <DisplayNameForm current={user.display_name} />
      <ChangePasswordForm />

      <div className="flex items-center gap-4 text-sm">
        <Link href="/" className="underline underline-offset-4">
          Back home
        </Link>
        <form action={signOut}>
          <button type="submit" data-testid="sign-out" className="underline underline-offset-4">
            Sign out
          </button>
        </form>
      </div>
    </main>
  );
}
