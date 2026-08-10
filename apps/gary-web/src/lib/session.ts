import { cookies } from "next/headers";
import { cache } from "react";

import { callApi, type SignedIn, type User } from "./api";

export const SESSION_COOKIE = "gary_session";

/** Set on gary-web's own origin, so it is first-party and survives Safari. */
export async function startSession(signedIn: SignedIn): Promise<void> {
  const store = await cookies();
  store.set(SESSION_COOKIE, signedIn.token, {
    httpOnly: true,
    sameSite: "lax",
    // Off over plain HTTP or the cookie is silently dropped in development.
    secure: process.env.NODE_ENV === "production",
    path: "/",
    expires: new Date(signedIn.expires_at),
  });
}

export async function endSession(): Promise<void> {
  const store = await cookies();
  store.delete(SESSION_COOKIE);
}

export async function sessionToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(SESSION_COOKIE)?.value ?? null;
}

/**
 * The signed-in user, or null. Null covers expired and revoked alike.
 *
 * Wrapped in React's cache so the several callers in one render — the app
 * layout needs it for the sidebar, the page needs it for its content —
 * share a single call to gary-api rather than asking it once each.
 */
export const currentUser = cache(async (): Promise<User | null> => {
  const token = await sessionToken();
  if (!token) {
    return null;
  }

  const result = await callApi<User>("/auth/me", { token });
  return result.ok ? result.data : null;
});
