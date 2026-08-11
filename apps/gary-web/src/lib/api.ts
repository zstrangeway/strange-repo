// Calls gary-api from the browser. Every request here is visible in devtools,
// which is the point: there is no server in between to hide anything, and no
// second log to correlate with.
//
// gary-api has to name this app's origin in BROWSER_ORIGINS or the browser
// makes the call and then refuses to hand back the answer.

import { getLogger, REQUEST_ID_HEADER, requestId } from "./logger";

const UNAVAILABLE = "gary is unavailable, try again shortly";

const log = getLogger("api");

export type ApiOk<T> = { ok: true; data: T };
export type ApiError = { ok: false; status: number; message: string };
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

async function messageFor(response: Response): Promise<string> {
  let detail: unknown;
  try {
    detail = (await response.json())?.detail;
  } catch {
    detail = undefined;
  }

  if (response.status === 422) {
    return validationMessage(detail);
  }
  if (typeof detail === "string") {
    return detail;
  }
  return UNAVAILABLE;
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
    return { ok: false, status: response.status, message: await messageFor(response) };
  }

  // 204 is not the only empty success: the reset endpoints answer 202 with no
  // body, and parsing that as JSON throws where the call plainly succeeded.
  const body = await response.text();
  if (!body) {
    return { ok: true, data: undefined as T };
  }

  return { ok: true, data: JSON.parse(body) as T };
}
