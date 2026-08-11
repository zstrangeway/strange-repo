import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@gary/ui/components/card";

import { FLASH_COOKIE, readFlash } from "@/lib/flash";
import { currentUser } from "@/lib/session";
import { absoluteUrl, withState } from "@/lib/urls";

import { connectedAccounts, waysToSignIn } from "../../actions";
import { ClearFlash } from "../../clear-flash";
import { Notice } from "../../form-parts";
import ConnectedAccounts from "./connected";
import { DisplayNameForm } from "./forms";

export default async function ProfilePage() {
  // See the note on the home page: the layout's guard does not stop this
  // from running, and currentUser is request-cached.
  const { error, confirmation } = readFlash(
    (await cookies()).get(FLASH_COOKIE)?.value,
  );
  const user = await currentUser();
  if (!user) {
    redirect("/login");
  }

  // Connecting sends you out to the provider and back, the same as signing
  // in — the callback tells the two apart by whether there is a session.
  const back = await absoluteUrl("/profile/connected");
  const [connected, offered] = await Promise.all([
    connectedAccounts(),
    waysToSignIn(back),
  ]);

  const connections = offered.map((provider) => {
    const held = connected.find((row) => row.provider === provider.name);
    return {
      provider: provider.name,
      label: provider.label,
      email: held?.email ?? null,
      authorizationUrl: withState(provider.authorization_url, provider.name),
    };
  });

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
          <CardTitle>Ways to sign in</CardTitle>
          <CardDescription>
            Connect another and either will reach this account. You cannot
            remove the last one.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {error || confirmation ? <ClearFlash /> : null}
          <Notice error={error} confirmation={confirmation} />
          <ConnectedAccounts connections={connections} />
        </CardContent>
      </Card>
    </div>
  );
}
