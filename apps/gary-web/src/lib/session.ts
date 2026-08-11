// Where the session token lives now that gary-web has no server of its own.
//
// localStorage, deliberately. It survives a refresh and a new tab, which is
// what "stay signed in" means to a person. The cost is that any script running
// on this page can read it, so an XSS bug is a stolen session rather than a
// defaced page — the trade a browser-only client makes in exchange for not
// having a server to hold an httpOnly cookie.

export const SESSION_KEY = "gary_session";

/** Guarded because this module is imported during the build, where there is
 *  no window and touching localStorage would throw. */
function storage(): Storage | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

export function storedToken(): string | null {
  return storage()?.getItem(SESSION_KEY) ?? null;
}

export function storeToken(token: string): void {
  storage()?.setItem(SESSION_KEY, token);
}

export function clearToken(): void {
  storage()?.removeItem(SESSION_KEY);
}
