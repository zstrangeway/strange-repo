"use client";

import { useState, useTransition } from "react";

import { Button } from "@gary/ui/components/button";
import { SubmitButton } from "@gary/ui/components/submit-button";

import { disconnectAccount, type Outcome } from "@/lib/gary";

import { Notice } from "../../form-parts";

export type Connection = {
  provider: string;
  label: string;
  email: string | null;
  authorizationUrl: string | null;
};

export default function ConnectedAccounts({
  connections,
  onChange,
}: {
  connections: Connection[];
  onChange: () => Promise<void>;
}) {
  const [outcome, setOutcome] = useState<Outcome>({});
  const [pending, start] = useTransition();
  const connectedCount = connections.filter((row) => row.email).length;

  function disconnect(provider: string) {
    start(async () => {
      const result = await disconnectAccount(provider);
      setOutcome(result);
      // The list is what changed, so it is refetched rather than patched —
      // gary-api decides what is connected, not this component.
      if (result.confirmation) {
        await onChange();
      }
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <Notice error={outcome.error} confirmation={outcome.confirmation} />

      {connections.map((row) => (
        <div
          key={row.provider}
          data-testid={`connection-${row.provider}`}
          className="flex items-center justify-between gap-4"
        >
          <div className="flex flex-col">
            <span className="text-sm font-medium">{row.label}</span>
            <span className="text-xs text-muted-foreground">
              {row.email ?? "Not connected"}
            </span>
          </div>

          {row.email ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                disconnect(row.provider);
              }}
            >
              {/* Disabled rather than hidden when it is the only one left:
                  the reason has to be visible, and gary-api refuses it
                  anyway — this only saves the round trip. */}
              <SubmitButton
                label="Disconnect"
                variant="outline"
                size="sm"
                pending={pending}
                disabled={connectedCount === 1}
                data-testid={`disconnect-${row.provider}`}
              />
            </form>
          ) : (
            <Button
              asChild
              variant="outline"
              size="sm"
              data-testid={`connect-${row.provider}`}
            >
              <a href={row.authorizationUrl ?? "#"}>Connect</a>
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}
