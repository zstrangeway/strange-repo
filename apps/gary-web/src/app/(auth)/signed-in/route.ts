import { NextResponse, type NextRequest } from "next/server";

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
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const result = await completeSignIn(
    provider,
    code,
    await absoluteUrl("/signed-in"),
  );

  if (result.error) {
    const back = new URL("/login", request.url);
    back.searchParams.set("error", result.error);
    return NextResponse.redirect(back);
  }

  return NextResponse.redirect(new URL("/", request.url));
}
