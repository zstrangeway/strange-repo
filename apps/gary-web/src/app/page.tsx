import Link from "next/link";
import { redirect } from "next/navigation";

import { currentUser } from "@/lib/session";

import { signOut } from "./actions";
import UnverifiedNotice from "./unverified-notice";

// The session is read per request, so this page can never be prerendered.
export const dynamic = "force-dynamic";

export default async function Home() {
  const user = await currentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <h1 data-testid="welcome" className="text-3xl font-semibold tracking-tight">
        Welcome Home, {user.display_name}
      </h1>

      {user.email_verified ? null : <UnverifiedNotice />}

      <div className="flex items-center gap-4 text-sm">
        <Link href="/profile" className="underline underline-offset-4">
          Profile
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
