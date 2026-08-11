import { type NextRequest } from "next/server";

import { seeOther } from "@/lib/redirects";
import { absoluteUrl } from "@/lib/urls";

import { connectAccount } from "../../../actions";

// Where a provider returns to when the point was connecting, not signing in.
// Separate from /signed-in so the two cannot be confused: this one needs a
// session and adds to it, that one creates one.
export async function GET(request: NextRequest) {
  const parameters = request.nextUrl.searchParams;
  const code = parameters.get("code");
  const provider = parameters.get("state");

  if (!code || !provider) {
    return seeOther("/profile");
  }

  const result = await connectAccount(
    provider,
    code,
    await absoluteUrl("/profile/connected"),
  );

  if (result.error) {
    return seeOther("/profile", { error: result.error });
  }
  if (result.confirmation) {
    return seeOther("/profile", { connected: result.confirmation });
  }

  return seeOther("/profile");
}
