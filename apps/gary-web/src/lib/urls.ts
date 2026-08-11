import { headers } from "next/headers";

/** Where a provider should send someone back to, as an absolute URL.
 *
 * Derived from the request rather than an environment variable: the specs
 * run on a different port from development and both differ from production,
 * and a redirect_uri that disagrees with the one the provider was given is
 * rejected — silently enough to be hard to place.
 */
export async function absoluteUrl(path: string): Promise<string> {
  const received = await headers();
  const host = received.get("host") ?? "localhost:3000";
  // Fly terminates TLS and forwards the original scheme; locally there is
  // none and the answer is http.
  const scheme = received.get("x-forwarded-proto") ?? "http";
  return `${scheme}://${host}${path}`;
}

/** Which provider came back is carried in state, since one callback serves
 *  all of them and the code alone does not say where it came from.
 *
 * Parsed and set rather than appended. gary-api builds the authorization URL
 * with an empty state for callers that have not chosen one yet, so appending
 * leaves that empty one in place and the URL carries state twice — which
 * Facebook rejects outright rather than reading the second.
 */
export function withState(url: string, provider: string): string {
  const target = new URL(url);
  target.searchParams.set("state", provider);
  return target.toString();
}
