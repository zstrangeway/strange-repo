/** A one-off message handed from a callback to the page it redirects to.
 *
 * The callbacks are Route Handlers, so they cannot render anything, and the
 * redirect is not optional either: the provider's code is single-use, so a
 * page rendered at the callback URL would break on refresh. Something has to
 * carry the outcome across that redirect.
 *
 * A cookie rather than a query parameter. A message in the address bar is one
 * anybody can put there — hand someone a link with ?error=<anything> and the
 * page renders it in our voice, which is a phishing surface for the price of
 * a URL. Nobody can set a cookie on this site from a link.
 */

export const FLASH_COOKIE = "gary_flash";

export type Flash = { error?: string; confirmation?: string };

// Long enough to survive the redirect, short enough that a message can never
// turn up attached to some later page. The client clears it on arrival; this
// is only the backstop for when that does not happen.
const LIFETIME_SECONDS = 30;

export function flashCookie(message: Flash): string {
  const value = encodeURIComponent(JSON.stringify(message));
  // Deliberately not HttpOnly: the page that shows this message is the thing
  // that clears it, and it clears it from the browser. There is nothing here
  // worth hiding from script — it is a sentence we wrote, not a credential.
  return (
    `${FLASH_COOKIE}=${value}; Path=/; Max-Age=${LIFETIME_SECONDS}; SameSite=Lax`
  );
}

export function readFlash(raw: string | undefined): Flash {
  if (!raw) {
    return {};
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    // Script can write this cookie, so it can hold anything at all.
    return {};
  }

  if (typeof parsed !== "object" || parsed === null) {
    return {};
  }

  const { error, confirmation } = parsed as Record<string, unknown>;
  return {
    ...(typeof error === "string" ? { error } : {}),
    ...(typeof confirmation === "string" ? { confirmation } : {}),
  };
}
