/** Send the browser on, without claiming to know where this app lives.
 *
 * The Location is deliberately relative. An absolute one has to name the
 * public origin, and nothing on the server reliably knows it: `request.url`
 * carries the address the server is bound to, which inside a container is
 * 0.0.0.0 — a URL the browser refuses outright, and only once the person is
 * already signed in. A relative Location is resolved against the URL the
 * browser actually asked for, so it is right in development, in the specs and
 * behind Fly's proxy without any of them having to agree on a hostname.
 *
 * Not to be confused with `absoluteUrl`: a redirect_uri really is absolute,
 * because the provider — not the browser — has to resolve it.
 */
export function seeOther(
  path: string,
  params: Record<string, string> = {},
): Response {
  const query = new URLSearchParams(params).toString();
  return new Response(null, {
    status: 303,
    headers: { Location: query ? `${path}?${query}` : path },
  });
}
