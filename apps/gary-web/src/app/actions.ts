"use server";

import { redirect } from "next/navigation";

import {
  callApi,
  type Identity,
  type Provider,
  type SignedIn,
  type User,
} from "@/lib/api";
import { endSession, sessionToken, startSession } from "@/lib/session";

export type FormState = { error?: string; confirmation?: string };

const NOT_SIGNED_IN = "You are not signed in";

function text(form: FormData, field: string): string {
  const value = form.get(field);
  return typeof value === "string" ? value : "";
}

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

/**
 * Redeem the code a provider handed back, and start a session.
 *
 * The code is exchanged from gary-web's server, never the browser: that is
 * what keeps gary-api's client secrets off the client, and what lets the
 * session cookie be first-party to gary-web.
 */
export async function completeSignIn(
  provider: string,
  code: string,
  redirectUri: string,
  displayName?: string,
): Promise<FormState> {
  const result = await callApi<SignedIn>("/auth/sessions", {
    method: "POST",
    body: {
      provider,
      code,
      redirect_uri: redirectUri,
      display_name: displayName,
    },
  });

  if (!result.ok) {
    return { error: result.message };
  }

  await startSession(result.data);
  // Outside the failure path on purpose: redirect works by throwing, so a
  // try/catch around it would swallow the navigation.
  redirect("/");
}

export async function signOut(): Promise<void> {
  const token = await sessionToken();
  // Drop the server session too, so the token is dead even if the cookie
  // was copied somewhere before it was cleared.
  await callApi("/auth/sessions/current", { method: "DELETE", token });
  await endSession();
  redirect("/login");
}

export async function updateDisplayName(
  _previous: FormState,
  form: FormData,
): Promise<FormState> {
  const token = await sessionToken();
  if (!token) {
    return { error: NOT_SIGNED_IN };
  }

  const result = await callApi<User>("/auth/me", {
    method: "PATCH",
    body: { display_name: text(form, "display_name") },
    token,
  });

  if (!result.ok) {
    return { error: result.message };
  }

  return { confirmation: "Your display name has been updated" };
}

export async function connectedAccounts(): Promise<Identity[]> {
  const token = await sessionToken();
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
  displayName?: string,
): Promise<FormState> {
  const token = await sessionToken();
  if (!token) {
    return { error: NOT_SIGNED_IN };
  }

  const result = await callApi<Identity>("/auth/me/identities", {
    method: "POST",
    body: {
      provider,
      code,
      redirect_uri: redirectUri,
      display_name: displayName,
    },
    token,
  });

  if (!result.ok) {
    return { error: result.message };
  }

  return { confirmation: `${result.data.label} is connected` };
}

export async function disconnectAccount(
  _previous: FormState,
  form: FormData,
): Promise<FormState> {
  const token = await sessionToken();
  if (!token) {
    return { error: NOT_SIGNED_IN };
  }

  const provider = text(form, "provider");
  const result = await callApi(`/auth/me/identities/${provider}`, {
    method: "DELETE",
    token,
  });

  if (!result.ok) {
    return { error: result.message };
  }

  return { confirmation: "That way of signing in has been removed" };
}
