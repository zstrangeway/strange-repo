"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { connectAccount } from "@/lib/gary";
import { setFlash } from "@/lib/flash";
import { callbackUrl } from "@/lib/urls";

// Where a provider returns to when the point was connecting, not signing in.
// Separate from /signed-in so the two cannot be confused: this one needs a
// session and adds to it, that one creates one. Being inside the app group
// means the layout has already established there is a session.
export default function Connected() {
  const router = useRouter();
  const started = useRef(false);

  useEffect(() => {
    if (started.current) {
      return;
    }
    started.current = true;

    const parameters = new URLSearchParams(window.location.search);
    const code = parameters.get("code");
    const provider = parameters.get("state");

    if (!code || !provider) {
      router.replace("/profile");
      return;
    }

    void connectAccount(provider, code, callbackUrl("/profile/connected")).then(
      (outcome) => {
        setFlash(outcome);
        router.replace("/profile");
      },
    );
  }, [router]);

  return null;
}
