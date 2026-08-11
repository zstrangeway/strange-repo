/** Where a provider should send someone back to, as an absolute URL.
 *
 * The browser knows its own origin, so there is nothing to derive and nothing
 * to get wrong. This used to be built on the server from forwarded headers,
 * which is how a redirect once pointed at 0.0.0.0.
 */
export function callbackUrl(path: string): string {
  return `${window.location.origin}${path}`;
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
