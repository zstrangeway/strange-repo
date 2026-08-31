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
  /** Why anybody would go. A situation nobody has been asked to do anything
   *  about is not an adventure. */
  hook: string;
  opening: string;
};

/** One way an edition lets you arrive at six scores. Which exist is the
 *  system's to say, never this app's — a list here would be a second place
 *  for the rules to live, and the first to go stale. */
export type Method = {
  slug: string;
  name: string;
  blurb: string;
  /** Whether gary produces the numbers. */
  generates: boolean;
  /** Whether you place them afterwards. Two questions and not one: rolling in
   *  order generates without arranging, and typing them in is the reverse. */
  arrange: boolean;
  /** Whether it spends the system's point budget. The third question, because
   *  the first two answer the same for point buy and for typing them in, and
   *  a page that told those apart by their slugs would be keeping a copy of
   *  the rules where nobody maintains it. */
  spends: boolean;
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
  methods: Method[];
  /** Why, when a system generates nothing. Empty for the ones that do. */
  cannot_generate: string;
  /** The lowest and highest a score may be. */
  scores: number[];
  /** What each score costs under this system's point buy, and the budget.
   *  Empty when it has none. Counted here while you spend; gary-api range
   *  checks what arrives like any other score. */
  point_costs: Record<string, number>;
  point_budget: number;
  /** What each score this system allows is worth on a check. A table from the
   *  system rather than arithmetic here, because the systems disagree about
   *  whether there is any: third edition onward halves the distance from ten,
   *  and first edition has a table per ability and no general modifier. */
  modifiers: Record<string, number>;
  modules: Module[];
};

/** One generated score, and the dice behind it. */
export type Score = {
  score: number;
  /** Kept rather than summed away: "15" and "6, 5, 4 and a discarded 1" are
   *  different things to read while deciding where to put it. */
  dice: number[];
  dropped: number | null;
};

export type Scores = {
  method: string;
  scores: Score[];
  /** Already placed, when the method does not let you arrange them. Null when
   *  they are yours to put where you like. */
  assigned: Record<string, number> | null;
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
  /** What the adventure is about, in the module's own words — a situation on
   *  screen before gary has written anything. */
  premise: string;
  /** Why the party is here — on screen from the moment the page loads, so
   *  the answer to "why am I here" is never only in gary's gift. */
  hook: string;
  /** Where the module starts. */
  place: string;
  turns: number;
  /** Whether anybody has spoken yet. False means gary has not opened. */
  begun: boolean;
  model: string;
  /** False when the model came from the deployment rather than the campaign. */
  model_chosen: boolean;
};

export type Character = {
  id: string;
  name: string;
  character_class: string;
  /** Both as created. What somebody currently is comes off the world, because
   *  a level is a fold over the log the same way hit points are. */
  level: number;
  experience: number;
  max_hp: number;
  abilities: Record<string, number>;
  /** "player" for the one you are, "gary" for the ones it speaks for. */
  played_by: string;
};

/** One thing the engines changed, as the stream sends it and as a turn keeps
 *  it. Open rather than a union of every kind: this app renders the few it
 *  has something to say about and passes the rest by, so a new kind in
 *  gary-api is not a build failure here. */
export type WorldChange = { kind: string } & Record<string, unknown>;

/** A character as they currently stand, projected from what has happened. */
export type Member = {
  id: string;
  name: string;
  character_class: string;
  level: number;
  experience: number;
  /** What the next level costs, or null when there is no next number to
   *  reach — at the top, and in a system that does not price a level at all.
   *  One answer for both, because a card has the same thing to say. */
  next_level: number | null;
  hp: number;
  max_hp: number;
  conditions: string[];
  down: boolean;
  played_by: string;
};

/** Something the party is fighting, as it currently stands. Its own shape
 *  rather than a Member with a flag: a monster has an armour class and no
 *  class, level or player. */
export type Foe = {
  id: string;
  name: string;
  hp: number;
  max_hp: number;
  armour_class: number;
  conditions: string[];
  down: boolean;
};

/** Turn order, decided once by the engine and folded back out of the log.
 *  `at` is a position rather than a name, because the name is in the list. */
export type Fight = {
  order: { id: string; name: string; side: "party" | "adversary" }[];
  at: number;
  round: number;
};

export type World = {
  place: string;
  minutes: number;
  facts: Record<string, string>;
  party: Member[];
  /** Everything fought, still standing or not: a monster that was killed is
   *  a fact about the campaign. */
  enemies: Foe[];
  /** Null when nobody is fighting, which is most of the time. */
  fight: Fight | null;
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
  /** Whose roll it was. Null for a roll about the world rather than about a
   *  person — how sound the timbers are, what the weather does. */
  character?: string | null;
  /** Which ability the modifier came off, when one did. Kept so a card can
   *  say "+3 dex" rather than "+3": a number with no provenance is a number
   *  somebody has to take on trust. */
  ability?: string | null;
  /** Which side rolled it, so a monster's roll reads as one without the page
   *  having to know every name at the table. */
  side?: "party" | "adversary";
};

/** A bounded stretch of play, and the unit of gary's memory: it is told this
 *  scene's turns and the recaps of the ones before it, never the whole
 *  campaign. */
export type Scene = {
  id: string;
  number: number;
  title: string;
  /** Null while a scene is being played, and also when it closed without gary
   *  being reachable to say what happened. `open` tells the two apart. */
  recap: string | null;
  open: boolean;
};

export type Turn = {
  id: string;
  role: "player" | "gm";
  content: string;
  complete: boolean;
  scene_id: string;
  /** Beside the turn they happened in, so a reloaded transcript shows a roll
   *  as a roll rather than losing it into the prose. */
  rolls: Roll[];
  /** What the turn changed, for the same reason — the stream carries both as
   *  they happen, and a reload would otherwise keep the prose and lose
   *  everything the engines did during it. */
  changes: WorldChange[];
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

  if (response.status === 422 && code === undefined) {
    // Validation has no code: the useful part is which field, which the
    // payload already carries. A refusal gary-api made on purpose does carry
    // one — a score outside what the system allows is a 422 with `bad_score`
    // on it — and that sentence says something worth reading, so it goes
    // through the same copy lookup as any other refusal rather than being
    // flattened into "that does not look right".
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
