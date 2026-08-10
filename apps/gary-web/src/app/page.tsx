import Link from "next/link";
import { redirect } from "next/navigation";

import { Button } from "@gary/ui/components/button";

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
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col items-center justify-center gap-8 p-6">
      <h1 data-testid="welcome" className="text-3xl font-semibold tracking-tight">
        Welcome Home, {user.display_name}
      </h1>

      {user.email_verified ? null : <UnverifiedNotice />}

      <div className="flex items-center gap-2">
        <Button asChild variant="link">
          <Link href="/profile">Profile</Link>
        </Button>
        <form action={signOut}>
          <Button type="submit" variant="link" data-testid="sign-out">
            Sign out
          </Button>
        </form>
      </div>
    </main>
  );
}
