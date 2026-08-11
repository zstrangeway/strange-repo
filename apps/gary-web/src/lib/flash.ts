// A message handed from a callback route to the page it navigates to.
//
// A variable, because that is all it needs to be now. The callback and the
// page it hands off to are the same running app — the navigation between them
// is client-side, so nothing is torn down in between. There is no redirect to
// survive, so there is no cookie and nothing in the address bar.
//
// Reading and clearing are separate on purpose. A read that also cleared would
// be an impure read, which React is free to run twice and which would come
// back empty the second time; the page reads it while rendering and clears it
// afterwards, which is the one order that works.

export type Flash = { error?: string; confirmation?: string };

let pending: Flash = {};

export function setFlash(message: Flash): void {
  pending = message;
}

/** What is waiting, if anything. Safe to call as often as you like. */
export function peekFlash(): Flash {
  return pending;
}

/** Drop it, so a message cannot turn up attached to some later page. */
export function clearFlash(): void {
  pending = {};
}
