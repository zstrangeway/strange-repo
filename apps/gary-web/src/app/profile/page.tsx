import Link from "next/link";
import { redirect } from "next/navigation";

import { Button } from "@gary/ui/components/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@gary/ui/components/card";

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
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center gap-6 p-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Your profile</h1>
        <p
          data-testid="profile-email"
          className="font-mono text-sm text-muted-foreground"
        >
          {user.email}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Display name</CardTitle>
          <CardDescription>What gary calls you.</CardDescription>
        </CardHeader>
        <CardContent>
          <DisplayNameForm current={user.display_name} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Password</CardTitle>
          <CardDescription>
            Changing it does not sign you out anywhere else.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ChangePasswordForm />
        </CardContent>
      </Card>

      <div className="flex items-center gap-2">
        <Button asChild variant="link">
          <Link href="/">Back home</Link>
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
