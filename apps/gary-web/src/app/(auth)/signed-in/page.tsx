"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { completeSignIn } from "@/lib/gary";
import { setFlash } from "@/lib/flash";
import { callbackUrl } from "@/lib/urls";

// Where a provider sends someone once they have agreed. A page now rather
// than a route handler: there is no cookie to set and no redirect to issue,
// only a code to redeem and a client-side navigation afterwards.
//
// The search string is read from window rather than useSearchParams so this
// page needs no Suspense boundary and can be exported as static.
export default function SignedIn() {
  const router = useRouter();
  // Effects run twice in development, and a provider's code is single-use:
  // redeeming it twice fails the second time and reports that as the outcome.
  const started = useRef(false);

  useEffect(() => {
    if (started.current) {
      return;
    }
    started.current = true;

    const parameters = new URLSearchParams(window.location.search);
    const code = parameters.get("code");
    const provider = parameters.get("state");

    // Someone who changed their mind at the provider comes back with an error
    // and no code. That is what pressing cancel does, not a failure, so it
    // returns them quietly rather than in a red box.
    if (!code || !provider) {
      router.replace("/login");
      return;
    }

    void completeSignIn(provider, code, callbackUrl("/signed-in")).then(
      (result) => {
        if (result.error) {
          setFlash({ error: result.error });
          router.replace("/login");
          return;
        }
        router.replace("/");
      },
    );
  }, [router]);

  return null;
}
