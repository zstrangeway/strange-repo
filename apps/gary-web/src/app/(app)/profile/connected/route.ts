import { NextResponse, type NextRequest } from "next/server";

import { absoluteUrl } from "@/lib/urls";

import { connectAccount } from "../../../actions";

// Where a provider returns to when the point was connecting, not signing in.
// Separate from /signed-in so the two cannot be confused: this one needs a
// session and adds to it, that one creates one.
export async function GET(request: NextRequest) {
  const parameters = request.nextUrl.searchParams;
  const code = parameters.get("code");
  const provider = parameters.get("state");
  const back = new URL("/profile", request.url);

  if (!code || !provider) {
    return NextResponse.redirect(back);
  }

  const result = await connectAccount(
    provider,
    code,
    await absoluteUrl("/profile/connected"),
  );

  if (result.error) {
    back.searchParams.set("error", result.error);
  } else if (result.confirmation) {
    back.searchParams.set("connected", result.confirmation);
  }

  return NextResponse.redirect(back);
}
