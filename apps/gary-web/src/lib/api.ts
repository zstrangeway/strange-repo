// Calls gary-api from gary-web's server, never from the browser. That is what
// lets the session cookie belong to gary-web's own origin — a cookie set by
// gary-api would be third-party here and dropped by Safari and Firefox.
//
// Worth knowing when debugging: none of these requests appear in browser
// devtools. They are in the gary-web server log.

const UNAVAILABLE = "gary is unavailable, try again shortly";

export type ApiOk<T> = { ok: true; data: T };
export type ApiError = { ok: false; status: number; message: string };
export type ApiResult<T> = ApiOk<T> | ApiError;

export type User = { id: string; email: string; display_name: string };
export type SignedIn = User & { token: string; expires_at: string };

function baseUrl(): string {
  // Read per request rather than at module load, so the deployed value is the
  // one Fly injected and not whatever was set when the image was built.
  return process.env.GARY_API_URL ?? "http://127.0.0.1:8000";
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
  const headers: Record<string, string> = {};
  if (options.body !== undefined) {
    headers["content-type"] = "application/json";
  }
  if (options.token) {
    headers["authorization"] = `Bearer ${options.token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: "no-store",
    });
  } catch (error) {
    // gary-api being down should read as "try again", not as a stack trace.
    console.error(`gary-api unreachable at ${baseUrl()}${path}:`, error);
    return { ok: false, status: 0, message: UNAVAILABLE };
  }

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
