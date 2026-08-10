import { redirect } from "next/navigation";

import { absoluteUrl } from "@/lib/urls";

import { connectAccount } from "../../../actions";

export const dynamic = "force-dynamic";

/**
 * Where a provider returns to when the point was connecting, not signing in.
 *
 * A separate callback from /signed-in so the two cannot be confused: this
 * one requires a session and adds to it, that one creates one.
 */
export default async function ConnectedCallback({
  searchParams,
}: PageProps<"/profile/connected">) {
  const { code, state } = await searchParams;

  if (typeof code === "string" && typeof state === "string") {
    await connectAccount(state, code, await absoluteUrl("/profile/connected"));
  }

  redirect("/profile");
}
