import { redirect } from "next/navigation";

import { Button } from "@gary/ui/components/button";
import { FormCard } from "@gary/ui/components/form-card";

import { currentUser } from "@/lib/session";
import { absoluteUrl } from "@/lib/urls";

import { waysToSignIn } from "../../actions";
import { Notice } from "../../form-parts";

export const dynamic = "force-dynamic";

const NOWHERE_TO_GO = "gary is unavailable, try again shortly";

export default async function LoginPage({
  searchParams,
}: PageProps<"/login">) {
  if (await currentUser()) {
    redirect("/");
  }

  const { error } = await searchParams;

  // The list comes from gary-api rather than being hard-coded here, so a
  // provider added or withdrawn there needs no change in this app.
  const providers = await waysToSignIn(await absoluteUrl("/signed-in"));

  return (
    <FormCard
      title={<h1 className="text-2xl">Sign in to gary</h1>}
      description="gary has no password of yours. Choose who should vouch for you."
    >
      <div className="flex flex-col gap-3">
        <Notice
          error={typeof error === "string" ? error : undefined}
        />
        {providers.length === 0 ? <Notice error={NOWHERE_TO_GO} /> : null}
        {providers.map((provider) => (
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

/** Which provider came back is carried in state, since one callback serves
 *  all of them and the code alone does not say where it came from. */
function withState(url: string, provider: string): string {
  const target = new URL(url);
  target.searchParams.set("state", provider);
  return target.toString();
}
