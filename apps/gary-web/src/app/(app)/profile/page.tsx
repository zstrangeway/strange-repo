"use client";

import { useCallback, useEffect, useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@gary/ui/components/card";

import { clearFlash, peekFlash, type Flash } from "@/lib/flash";
import { connectedAccounts, waysToSignIn } from "@/lib/gary";
import { callbackUrl, withState } from "@/lib/urls";
import { useSession } from "@/lib/use-session";

import { Notice } from "../../form-parts";
import ConnectedAccounts, { type Connection } from "./connected";
import { DisplayNameForm } from "./forms";

export default function ProfilePage() {
  const { user } = useSession();
  const [connections, setConnections] = useState<Connection[]>([]);
  // Read while rendering, cleared afterwards. The read is pure, so React may
  // do it as many times as it likes; the clearing is the effect.
  const [flash] = useState<Flash>(peekFlash);
  useEffect(() => clearFlash, []);

  const load = useCallback(async () => {
    // Connecting sends you out to the provider and back, the same as signing
    // in — the callback tells the two apart by whether there is a session.
    const back = callbackUrl("/profile/connected");
    const [connected, offered] = await Promise.all([
      connectedAccounts(),
      waysToSignIn(back),
    ]);

    setConnections(
      offered.map((provider) => {
        const held = connected.find((row) => row.provider === provider.name);
        return {
          provider: provider.name,
          label: provider.label,
          email: held?.email ?? null,
          authorizationUrl: withState(provider.authorization_url, provider.name),
        };
      }),
    );
  }, []);

  useEffect(() => {
    // Fetching on mount, which is what an effect is for. The rule below is
    // aimed at state derived from other state; this is an external system.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  if (!user) {
    return null;
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
          <CardTitle>Ways to sign in</CardTitle>
          <CardDescription>
            Connect another and either will reach this account. You cannot
            remove the last one.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Notice error={flash.error} confirmation={flash.confirmation} />
          <ConnectedAccounts connections={connections} onChange={load} />
        </CardContent>
      </Card>
    </div>
  );
}
