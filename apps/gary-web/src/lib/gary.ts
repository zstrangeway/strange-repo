// Everything gary-web asks of gary-api, in one place.
//
// This replaces the server actions. Each of these runs in the browser and
// carries the stored token itself, so no caller has to remember to attach it
// — forgetting was the failure mode worth designing out.

import {
  callApi,
  type Campaign,
  type Character,
  type Identity,
  type Model,
  type Provider,
  type Scene,
  type SignedIn,
  type System,
  type Turn,
  type User,
  type World,
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


// ---------------------------------------------------------------- the game

/** The systems gary runs and the modules written for them. No session: it is
 *  a menu, and it is part of deciding whether to make an account. */
export async function catalogue(): Promise<System[]> {
  const result = await callApi<System[]>("/catalogue");
  return result.ok ? result.data : [];
}

/** One system and everything it can say about itself — its classes, most of
 *  all, which is what a character sheet is offered. */
export async function systemNamed(slug: string): Promise<System | null> {
  const result = await callApi<System>(`/catalogue/${slug}`);
  return result.ok ? result.data : null;
}

/** The models gary can be run on. Only ones that can call tools are offered —
 *  gary's design is the model going through the engines, and one that cannot
 *  call a tool would narrate a game nothing was adjudicating. */
export async function runnableModels(): Promise<Model[]> {
  const result = await callApi<Model[]>("/models");
  return result.ok ? result.data : [];
}

export async function myCampaigns(): Promise<Campaign[]> {
  const result = await callApi<Campaign[]>("/campaigns", {
    token: storedToken(),
  });
  return result.ok ? result.data : [];
}

export async function campaign(id: string): Promise<Campaign | null> {
  const result = await callApi<Campaign>(`/campaigns/${id}`, {
    token: storedToken(),
  });
  return result.ok ? result.data : null;
}

export async function startCampaign(fields: {
  name: string;
  system: string;
  module: string;
  model: string | null;
}): Promise<Outcome & { campaign?: Campaign }> {
  const result = await callApi<Campaign>("/campaigns", {
    method: "POST",
    body: fields,
    token: storedToken(),
  });

  return result.ok ? { campaign: result.data } : { error: result.message };
}

/** Move a campaign to another model, mid-game. Null hands it back to the
 *  deployment's default. */
export async function changeModel(
  id: string,
  model: string | null,
): Promise<Outcome & { campaign?: Campaign }> {
  const result = await callApi<Campaign>(`/campaigns/${id}`, {
    method: "PATCH",
    body: { model },
    token: storedToken(),
  });

  return result.ok ? { campaign: result.data } : { error: result.message };
}

export async function addCharacter(
  id: string,
  fields: { name: string; character_class: string },
): Promise<Outcome & { character?: Character }> {
  const result = await callApi<Character>(`/campaigns/${id}/characters`, {
    method: "POST",
    body: fields,
    token: storedToken(),
  });

  return result.ok ? { character: result.data } : { error: result.message };
}

/** The party as they currently stand — hit points and conditions projected
 *  from everything that has happened, not read off the sheet. */
export async function worldOf(id: string): Promise<World | null> {
  const result = await callApi<World>(`/campaigns/${id}/world`, {
    token: storedToken(),
  });
  return result.ok ? result.data : null;
}

/** Every scene, oldest first, with what each is remembered by. */
export async function scenesOf(id: string): Promise<Scene[]> {
  const result = await callApi<Scene[]>(`/campaigns/${id}/scenes`, {
    token: storedToken(),
  });
  return result.ok ? result.data : [];
}

/** End the scene being played and start the next one. Slow on purpose: this
 *  is what runs the reconciliation pass. */
export async function beginScene(
  id: string,
  title: string,
): Promise<Outcome & { scene?: Scene }> {
  const result = await callApi<Scene>(`/campaigns/${id}/scenes`, {
    method: "POST",
    body: { title },
    token: storedToken(),
  });

  return result.ok ? { scene: result.data } : { error: result.message };
}

/** Everything said so far. The stream only carries what happens next, so a
 *  reload has to ask for the rest. */
export async function transcript(id: string): Promise<Turn[]> {
  const result = await callApi<Turn[]>(`/campaigns/${id}/turns`, {
    token: storedToken(),
  });
  return result.ok ? result.data : [];
}
