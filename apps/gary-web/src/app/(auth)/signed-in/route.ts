import { type NextRequest } from "next/server";

import { seeOther } from "@/lib/redirects";
import { absoluteUrl } from "@/lib/urls";

import { completeSignIn } from "../../actions";

// A Route Handler rather than a page, and not by preference: starting a
// session means setting a cookie, and Next only allows that in a Server
// Action or a Route Handler. A page that sets one throws at render.
export async function GET(request: NextRequest) {
  const parameters = request.nextUrl.searchParams;
  const code = parameters.get("code");
  const provider = parameters.get("state");

  // Someone who changed their mind at the provider comes back with an error
  // and no code. That is what pressing cancel does, not a failure, so it
  // returns them quietly rather than in a red box.
  if (!code || !provider) {
    return seeOther("/login");
  }

  const result = await completeSignIn(
    provider,
    code,
    await absoluteUrl("/signed-in"),
  );

  if (result.error) {
    return seeOther("/login", { error: result.error });
  }

  return seeOther("/");
}
