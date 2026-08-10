import { redirect } from "next/navigation";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@gary/ui/components/card";

import { currentUser } from "@/lib/session";

import { ChangePasswordForm, DisplayNameForm } from "./forms";

export default async function ProfilePage() {
  // See the note on the home page: the layout's guard does not stop this
  // from running, and currentUser is request-cached.
  const user = await currentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">Your profile</h1>
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
    </div>
  );
}
