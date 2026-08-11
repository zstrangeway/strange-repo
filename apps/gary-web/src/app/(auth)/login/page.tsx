"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@gary/ui/components/button";
import { FormCard } from "@gary/ui/components/form-card";

import type { Provider } from "@/lib/api";
import { clearFlash, peekFlash, type Flash } from "@/lib/flash";
import { me, waysToSignIn } from "@/lib/gary";
import { callbackUrl, withState } from "@/lib/urls";

import { Notice } from "../../form-parts";

const NOWHERE_TO_GO = "gary is unavailable, try again shortly";

export default function LoginPage() {
  const router = useRouter();
  const [providers, setProviders] = useState<Provider[] | null>(null);
  // Read while rendering, cleared afterwards. The read is pure, so React may
  // do it as many times as it likes; the clearing is the effect.
  const [flash] = useState<Flash>(peekFlash);
  useEffect(() => clearFlash, []);

  useEffect(() => {
    void me().then((user) => {
      if (user) {
        router.replace("/");
        return;
      }
      // The list comes from gary-api rather than being hard-coded here, so a
      // provider added or withdrawn there needs no change in this app.
      void waysToSignIn(callbackUrl("/signed-in")).then(setProviders);
    });
  }, [router]);

  return (
    <FormCard
      title={<h1 className="text-2xl">Sign in to gary</h1>}
      description="gary has no password of yours. Choose who should vouch for you."
    >
      <div className="flex flex-col gap-3">
        <Notice error={flash.error} />
        {providers?.length === 0 ? <Notice error={NOWHERE_TO_GO} /> : null}
        {(providers ?? []).map((provider) => (
          <Button
            key={provider.name}
            asChild
            variant="outline"
            data-testid={`sign-in-${provider.name}`}
          >
            {/* A plain link, not a fetch: the provider needs the browser to
                travel to it so the person can see whose page they are on. */}
            <a href={withState(provider.authorization_url, provider.name)}>
              Continue with {provider.label}
            </a>
          </Button>
        ))}
      </div>
    </FormCard>
  );
}
