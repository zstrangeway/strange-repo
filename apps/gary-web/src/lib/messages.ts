// What gary-web says when gary-api refuses.
//
// Keyed on the code, not the sentence. gary-api sends both — the sentence for
// a log and for a client with nothing better — but the words on screen are
// this app's to choose, so they can be changed here without touching an API
// that iOS and Android would be reading too.
//
// A code with no entry falls through to whatever gary-api said, which is
// better than a shrug and is how a refusal added there shows up here before
// anyone gets round to writing copy for it.

const OURS: Record<string, string> = {
  provider_refused: "That did not work. Try again.",
  unknown_provider: "That is not a way to sign in to gary.",
  identity_taken: "That account is already connected to another gary account.",
  last_identity: "That is your only way to sign in, so it cannot be removed.",
  not_connected: "That is not connected.",
};

export function messageFor(code: string | undefined, fallback: string): string {
  return (code && OURS[code]) || fallback;
}
