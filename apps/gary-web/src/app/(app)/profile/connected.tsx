"use client";

import { useActionState } from "react";

import { Button } from "@gary/ui/components/button";
import { SubmitButton } from "@gary/ui/components/submit-button";

import { disconnectAccount, type FormState } from "../../actions";
import { Notice } from "../../form-parts";

type Connection = {
  provider: string;
  label: string;
  email: string | null;
  authorizationUrl: string | null;
};

export default function ConnectedAccounts({
  connections,
}: {
  connections: Connection[];
}) {
  const [state, action] = useActionState<FormState, FormData>(
    disconnectAccount,
    {},
  );
  const connectedCount = connections.filter((row) => row.email).length;

  return (
    <div className="flex flex-col gap-4">
      <Notice error={state.error} confirmation={state.confirmation} />

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
            <form action={action}>
              <input type="hidden" name="provider" value={row.provider} />
              {/* Disabled rather than hidden when it is the only one left:
                  the reason has to be visible, and gary-api refuses it
                  anyway — this only saves the round trip. */}
              <SubmitButton
                label="Disconnect"
                variant="outline"
                size="sm"
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
