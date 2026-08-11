// Calls gary-api from the browser. Every request here is visible in devtools,
// which is the point: there is no server in between to hide anything, and no
// second log to correlate with.
//
// gary-api has to name this app's origin in BROWSER_ORIGINS or the browser
// makes the call and then refuses to hand back the answer.

import { getLogger, REQUEST_ID_HEADER, requestId } from "./logger";
import { messageFor as copyFor } from "./messages";

const UNAVAILABLE = "gary is unavailable, try again shortly";

const log = getLogger("api");

export type ApiOk<T> = { ok: true; data: T };
export type ApiError = {
  ok: false;
  status: number;
  message: string;
  /** gary-api's machine-readable reason, where it has one. */
  code?: string;
};
export type ApiResult<T> = ApiOk<T> | ApiError;

export type User = {
  id: string;
  email: string;
  display_name: string;
};

/** One way of signing in to an account. An account may have several. */
export type Identity = {
  provider: string;
  label: string;
  email: string;
  connected_at: string;
};

/** A way of signing in that gary offers, and where to send someone for it. */
export type Provider = {
  name: string;
  label: string;
  authorization_url: string;
};
export type SignedIn = User & { token: string; expires_at: string };

/** One adventure written for a system. */
export type Module = {
  slug: string;
  title: string;
  premise: string;
  opening: string;
};

/** A ruleset gary can run, and everything it can say about itself. */
export type System = {
  slug: string;
  name: string;
  blurb: string;
  classes: string[];
  abilities: string[];
  /** How many ways this system grades a check. Two for most, four for some. */
  degrees: string[];
  modules: Module[];
};

/** A model gary can be run on. Only ones that can call tools are offered. */
export type Model = {
  id: string;
  name: string;
  /** Dollars per million tokens — the unit the difference is legible in. */
  prompt_cost: number;
  completion_cost: number;
  context: number;
  reasons: boolean;
  suggested: boolean;
};

export type Campaign = {
  id: string;
  name: string;
  system: string;
  module: string;
  title: string;
  turns: number;
  model: string;
  /** False when the model came from the deployment rather than the campaign. */
  model_chosen: boolean;
};

export type Character = {
  id: string;
  name: string;
  character_class: string;
  level: number;
  max_hp: number;
  abilities: Record<string, number>;
};

/** A character as they currently stand, projected from what has happened. */
export type Member = {
  id: string;
  name: string;
  character_class: string;
  level: number;
  hp: number;
  max_hp: number;
  conditions: string[];
  down: boolean;
};

export type World = {
  place: string;
  minutes: number;
  facts: Record<string, string>;
  party: Member[];
};

/** A roll that happened — gary asked, gary-api rolled, and where there was a
 *  DC the rules graded it. Never a number gary produced. */
export type Roll = {
  notation: string;
  dice: number[];
  modifier: number;
  total: number;
  reason: string;
  /** Set when the roll was a check rather than a bare roll. */
  dc?: number | null;
  degree?: string | null;
  character?: string;
};

export type Turn = {
  id: string;
  role: "player" | "gm";
  content: string;
  complete: boolean;
  /** Beside the turn they happened in, so a reloaded transcript shows a roll
   *  as a roll rather than losing it into the prose. */
  rolls: Roll[];
};

function baseUrl(): string {
  // Baked in at build time, not read at runtime: this code runs in a browser,
  // which has no environment to read. Changing where gary-api lives means a
  // rebuild, which is the honest cost of shipping a static app.
  return process.env.NEXT_PUBLIC_GARY_API_URL ?? "http://127.0.0.1:8000";
}

/** Turns FastAPI's validation payload into something a person can act on. */
function validationMessage(detail: unknown): string {
  if (!Array.isArray(detail) || detail.length === 0) {
    return "That does not look right, please check and try again";
  }

  const first = detail[0] as { loc?: unknown[]; msg?: string };
  const field = Array.isArray(first.loc) ? String(first.loc.at(-1)) : "";

  if (field === "password" || field === "new_password") {
    return "Your password needs to be at least 8 characters";
  }
  if (field === "email") {
    return "That does not look like an email address";
  }
  if (field === "display_name") {
    return "Your display name cannot be blank";
  }

  return first.msg ?? "That does not look right, please check and try again";
}

async function refusalFrom(
  response: Response,
): Promise<{ message: string; code?: string }> {
  let body: { detail?: unknown; code?: unknown } = {};
  try {
    body = (await response.json()) ?? {};
  } catch {
    body = {};
  }

  const code = typeof body.code === "string" ? body.code : undefined;

  if (response.status === 422) {
    // Validation has no code: the useful part is which field, which the
    // payload already carries.
    return { message: validationMessage(body.detail) };
  }

  const said = typeof body.detail === "string" ? body.detail : UNAVAILABLE;
  return { message: copyFor(code, said), code };
}

export async function callApi<T>(
  path: string,
  options: { method?: string; body?: unknown; token?: string | null } = {},
): Promise<ApiResult<T>> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = {};
  if (options.body !== undefined) {
    headers["content-type"] = "application/json";
  }
  if (options.token) {
    headers["authorization"] = `Bearer ${options.token}`;
  }

  // Handed to gary-api, which keeps an inbound id rather than minting its
  // own. That is what makes one action findable in both logs at once.
  const request_id = requestId();
  headers[REQUEST_ID_HEADER] = request_id;

  const started = performance.now();
  const elapsed = () => Math.round((performance.now() - started) * 1000) / 1000;

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}${path}`, {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: "no-store",
    });
  } catch (error) {
    // gary-api being down should read as "try again", not as a stack trace.
    log.error("api.unreachable", {
      request_id,
      method,
      path,
      url: baseUrl(),
      duration_ms: elapsed(),
      error,
    });
    return { ok: false, status: 0, message: UNAVAILABLE };
  }

  log.info("api.call", {
    request_id,
    method,
    path,
    status: response.status,
    duration_ms: elapsed(),
  });

  if (!response.ok) {
    const refusal = await refusalFrom(response);
    return { ok: false, status: response.status, ...refusal };
  }

  // 204 is not the only empty success: the reset endpoints answer 202 with no
  // body, and parsing that as JSON throws where the call plainly succeeded.
  const body = await response.text();
  if (!body) {
    return { ok: true, data: undefined as T };
  }

  try {
    return { ok: true, data: JSON.parse(body) as T };
  } catch (error) {
    // A 200 carrying a proxy error page or a truncated body. This used to
    // throw out of here and be caught by Next as a server crash; there is no
    // server to crash now, so it would have thrown inside a render and shown
    // a blank page with the reason in nobody's hands.
    log.error("api.unreadable", {
      request_id,
      method,
      path,
      status: response.status,
      duration_ms: elapsed(),
      error,
    });
    return { ok: false, status: response.status, message: UNAVAILABLE };
  }
}
