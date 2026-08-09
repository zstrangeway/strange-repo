"use server";

import { redirect } from "next/navigation";

import { callApi, type SignedIn, type User } from "@/lib/api";
import {
  endSession,
  sessionToken,
  startSession,
} from "@/lib/session";

export type FormState = { error?: string; confirmation?: string };

const NOT_SIGNED_IN = "You are not signed in";

function text(form: FormData, field: string): string {
  const value = form.get(field);
  return typeof value === "string" ? value : "";
}

export async function signUp(
  _previous: FormState,
  form: FormData,
): Promise<FormState> {
  const result = await callApi<SignedIn>("/auth/register", {
    method: "POST",
    body: {
      email: text(form, "email"),
      password: text(form, "password"),
      display_name: text(form, "display_name"),
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

export async function signIn(
  _previous: FormState,
  form: FormData,
): Promise<FormState> {
  const result = await callApi<SignedIn>("/auth/sessions", {
    method: "POST",
    body: { email: text(form, "email"), password: text(form, "password") },
  });

  if (!result.ok) {
    return { error: result.message };
  }

  await startSession(result.data);
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

export async function requestPasswordReset(
  _previous: FormState,
  form: FormData,
): Promise<FormState> {
  await callApi("/auth/password-reset", {
    method: "POST",
    body: { email: text(form, "email") },
  });

  // The same answer whether or not the address is known. Anything else makes
  // this page a way to ask gary who has an account.
  return {
    confirmation: "If that address has an account, a reset link is on its way",
  };
}

export async function confirmPasswordReset(
  _previous: FormState,
  form: FormData,
): Promise<FormState> {
  const result = await callApi("/auth/password-reset/confirm", {
    method: "POST",
    body: {
      token: text(form, "token"),
      new_password: text(form, "new_password"),
    },
  });

  if (!result.ok) {
    return { error: result.message };
  }

  redirect("/login?reset=1");
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

export async function changePassword(
  _previous: FormState,
  form: FormData,
): Promise<FormState> {
  const token = await sessionToken();
  if (!token) {
    return { error: NOT_SIGNED_IN };
  }

  const result = await callApi("/auth/me/password", {
    method: "POST",
    body: {
      current_password: text(form, "current_password"),
      new_password: text(form, "new_password"),
    },
    token,
  });

  if (!result.ok) {
    return { error: result.message };
  }

  return { confirmation: "Your password has been changed" };
}
