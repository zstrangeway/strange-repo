// Everything gary-web asks of gary-api, in one place.
//
// This replaces the server actions. Each of these runs in the browser and
// carries the stored token itself, so no caller has to remember to attach it
// — forgetting was the failure mode worth designing out.

import {
  callApi,
  type Identity,
  type Provider,
  type SignedIn,
  type User,
} from "./api";
import { clearToken, storedToken, storeToken } from "./session";

export type Outcome = { error?: string; confirmation?: string };

const NOT_SIGNED_IN = "You are not signed in";

/**
 * The ways in, and where each one sends you.
 *
 * Asked of gary-api rather than built here, so the day a fourth provider is
 * added no client needs rebuilding — including the ones that are not this
 * one.
 */
export async function waysToSignIn(redirectUri: string): Promise<Provider[]> {
  const result = await callApi<Provider[]>(
    `/auth/providers?redirect_uri=${encodeURIComponent(redirectUri)}`,
  );
  return result.ok ? result.data : [];
}

/** Who the stored token belongs to, or null. Covers expired and revoked
 *  alike: gary-api is the only thing that can say, so it is asked. */
export async function me(): Promise<User | null> {
  const token = storedToken();
  if (!token) {
    return null;
  }

  const result = await callApi<User>("/auth/me", { token });
  if (!result.ok) {
    // A token gary-api will not honour is worse than no token: it makes every
    // later call fail in a way that looks like a bug rather than a sign-out.
    if (result.status === 401) {
      clearToken();
    }
    return null;
  }

  return result.data;
}

export async function completeSignIn(
  provider: string,
  code: string,
  redirectUri: string,
): Promise<Outcome> {
  const result = await callApi<SignedIn>("/auth/sessions", {
    method: "POST",
    body: { provider, code, redirect_uri: redirectUri },
  });

  if (!result.ok) {
    return { error: result.message };
  }

  storeToken(result.data.token);
  return {};
}

export async function signOut(): Promise<void> {
  const token = storedToken();
  // Ended at gary-api too, so the token is dead rather than merely forgotten
  // — anything that copied it out of storage stops working as well.
  await callApi("/auth/sessions/current", { method: "DELETE", token });
  clearToken();
}

export async function updateDisplayName(name: string): Promise<Outcome> {
  const token = storedToken();
  if (!token) {
    return { error: NOT_SIGNED_IN };
  }

  const result = await callApi<User>("/auth/me", {
    method: "PATCH",
    body: { display_name: name },
    token,
  });

  return result.ok
    ? { confirmation: "Your display name has been updated" }
    : { error: result.message };
}

export async function connectedAccounts(): Promise<Identity[]> {
  const token = storedToken();
  if (!token) {
    return [];
  }

  const result = await callApi<Identity[]>("/auth/me/identities", { token });
  return result.ok ? result.data : [];
}

export async function connectAccount(
  provider: string,
  code: string,
  redirectUri: string,
): Promise<Outcome> {
  const token = storedToken();
  if (!token) {
    return { error: NOT_SIGNED_IN };
  }

  const result = await callApi<Identity>("/auth/me/identities", {
    method: "POST",
    body: { provider, code, redirect_uri: redirectUri },
    token,
  });

  return result.ok
    ? { confirmation: `${result.data.label} is connected` }
    : { error: result.message };
}

export async function disconnectAccount(provider: string): Promise<Outcome> {
  const token = storedToken();
  if (!token) {
    return { error: NOT_SIGNED_IN };
  }

  const result = await callApi(`/auth/me/identities/${provider}`, {
    method: "DELETE",
    token,
  });

  return result.ok
    ? { confirmation: "That way of signing in has been removed" }
    : { error: result.message };
}
