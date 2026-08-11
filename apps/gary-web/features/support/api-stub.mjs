import http from "node:http";
import { randomUUID } from "node:crypto";

// A stand-in for gary-api, holding accounts, identities and sessions in
// memory, plus a stand-in for the providers themselves.
//
// It owes gary-api a contract, not an implementation: statuses and bodies
// here must match what apps/gary-api's own specs assert, or these specs pass
// against a service that does not exist.
//
// The provider half matters more than it looks. Signing in is a real browser
// navigation out to somebody else and back, so a double that only answered
// API calls would skip the half most likely to be wrong. /fake/{provider}
// answers that navigation and bounces straight back with a code, which is
// what a provider does once someone has agreed.

const PORT = 8799;

export const BASE_URL = `http://127.0.0.1:${PORT}`;

const LABELS = { google: "Google", facebook: "Facebook", apple: "Apple" };

let server = null;
let answeringWithGarbage = false;
let providers = ["google", "facebook", "apple"];

const users = new Map(); // id -> {id, email, display_name}
const identities = new Map(); // `${provider}:${subject}` -> {user_id, email}
const sessions = new Map(); // token -> user_id
// Who the next trip to a given provider will come back as. Set by a scenario
// so it can say who is signing in at the moment it signs them in.
const waiting = new Map(); // provider -> {subject, email, name}

const campaigns = new Map(); // id -> {id, user_id, name, system, module, model}
const characters = new Map(); // id -> {id, campaign_id, name, ...}
const turns = new Map(); // id -> {id, campaign_id, role, content, rolls, at}

// What the next turn will be. A scenario says what gary does at the moment it
// sends the message, exactly as it says who is signing in — no state left
// over from a previous scenario, and nothing to leak between them.
let plan = null;
// Resolved by garyFinishes(). Every turn holds its stream open until then, so
// a scenario can assert on a turn that is still being written — which is the
// half of streaming a browser can actually see.
let release = null;

const DEFAULT_HP = 8;

// The catalogue, and it owes gary-api these exact slugs and titles. A stub
// that invented its own would let these specs pass against a service where
// every one of these pages 404s.
const CATALOGUE = [
  {
    slug: "dnd-5e",
    name: "Dungeons & Dragons 5th Edition",
    blurb: "Roll a d20, add a modifier, meet a difficulty class.",
    classes: ["fighter", "rogue", "wizard"],
    abilities: ["strength", "dexterity", "constitution"],
    degrees: ["success", "failure"],
    modules: [
      {
        slug: "the-drowned-belfry",
        title: "The Drowned Belfry",
        premise: "A bell tower sunk to its eaves in the marsh outside Ashfen.",
        opening: "the causeway into Ashfen marsh, at dusk",
      },
      {
        slug: "the-ashfen-road",
        title: "The Ashfen Road",
        premise: "Three carters gone on a road with nowhere to hide.",
        opening: "the last waystation before the missing stretch of road",
      },
    ],
  },
  {
    slug: "pathfinder-2e",
    name: "Pathfinder 2nd Edition",
    blurb: "Four degrees of success, and a natural 20 shifts the ladder.",
    classes: ["fighter", "rogue"],
    abilities: ["strength", "dexterity", "constitution"],
    degrees: [
      "critical success",
      "success",
      "failure",
      "critical failure",
    ],
    modules: [
      {
        slug: "salt-and-cinder",
        title: "Salt and Cinder",
        premise: "A quay that burns without smoke.",
        opening: "the burnt quay at Cinderfall",
      },
    ],
  },
];

const MODELS = [
  {
    id: "anthropic/claude-opus-5",
    name: "Claude Opus 5",
    prompt_cost: 5.0,
    completion_cost: 25.0,
    context: 1000000,
    reasons: true,
    suggested: true,
  },
  {
    id: "deepseek/deepseek-v3.2",
    name: "DeepSeek V3.2",
    prompt_cost: 0.27,
    completion_cost: 0.4,
    context: 163840,
    reasons: true,
    suggested: true,
  },
  {
    id: "anthropic/claude-sonnet-5",
    name: "Claude Sonnet 5",
    prompt_cost: 2.0,
    completion_cost: 10.0,
    context: 1000000,
    reasons: true,
    suggested: true,
  },
  {
    id: "anthropic/claude-haiku-4.5",
    name: "Claude Haiku 4.5",
    prompt_cost: 1.0,
    completion_cost: 5.0,
    context: 200000,
    reasons: false,
    suggested: false,
  },
];

// What gary-api runs a campaign on when it names no model. Named rather than
// taken off the front of MODELS, because gary-api names it too — the list
// leads with what to suggest and that is not what to bill by default.
const FALLBACK_MODEL = "anthropic/claude-sonnet-5";

export function answerWithGarbage() {
  answeringWithGarbage = true;
}

export function reset() {
  users.clear();
  identities.clear();
  sessions.clear();
  waiting.clear();
  campaigns.clear();
  characters.clear();
  turns.clear();
  providers = ["google", "facebook", "apple"];
  answeringWithGarbage = false;
  plan = null;
  // Let go of anything still held, or the scenario that held it leaves a
  // socket open and the next one waits on it.
  garyFinishes();
}

/** What gary will do with the next thing said to it. */
export function garyWill(next) {
  plan = next;
}

/** Let the open turn end. Called by a scenario that has finished asserting on
 *  a turn mid-flight, and by reset so nothing outlives its scenario. */
export function garyFinishes() {
  const held = release;
  release = null;
  held?.();
}

export function addCampaign(userId, { name, system, module, model }) {
  const campaign = {
    id: randomUUID(),
    user_id: userId,
    name,
    system: system ?? "dnd-5e",
    module: module ?? "the-drowned-belfry",
    model: model ?? null,
    at: campaigns.size,
  };
  campaigns.set(campaign.id, campaign);
  return campaign;
}

export function addCharacterTo(campaignId, { name, character_class }) {
  const character = {
    id: randomUUID(),
    campaign_id: campaignId,
    name,
    character_class,
    level: 1,
    max_hp: DEFAULT_HP,
    abilities: { strength: 10, dexterity: 10, constitution: 10 },
    at: characters.size,
  };
  characters.set(character.id, character);
  return character;
}

export function campaignCalled(name) {
  return [...campaigns.values()].find((one) => one.name === name);
}

function moduleIn(system, slug) {
  return CATALOGUE.find((one) => one.slug === system)?.modules.find(
    (one) => one.slug === slug,
  );
}

function asCampaign(campaign) {
  return {
    id: campaign.id,
    name: campaign.name,
    system: campaign.system,
    module: campaign.module,
    title: moduleIn(campaign.system, campaign.module)?.title ?? "",
    turns: [...turns.values()].filter((one) => one.campaign_id === campaign.id)
      .length,
    // Resolved, never null — a client should not have to know what the
    // deployment's default is to render which model a campaign runs on.
    model: campaign.model ?? FALLBACK_MODEL,
    model_chosen: campaign.model !== null,
  };
}

function partyOf(campaignId) {
  return [...characters.values()]
    .filter((one) => one.campaign_id === campaignId)
    .sort((a, b) => a.at - b.at);
}

/** Who the next sign-in at this provider will be. */
export function nextPerson(provider, { subject, email, name }) {
  waiting.set(provider, { subject: subject ?? `subject-of-${email}`, email, name });
}

export function onlyProviders(names) {
  providers = names;
}

/** An account that already exists, as if someone had signed in before. */
export function addAccount(provider, { subject, email, name }) {
  const user = { id: randomUUID(), email, display_name: name };
  users.set(user.id, user);
  identities.set(`${provider}:${subject ?? `subject-of-${email}`}`, {
    user_id: user.id,
    email,
    provider,
    connected_at: new Date().toISOString(),
  });
  return user;
}

/** The one account a scenario signed in. Steps that arrange a campaign do
 *  not know the address, and there is only ever one. */
export function onlyAccount() {
  return [...users.values()][0];
}

export function accountFor(email) {
  return [...users.values()].find((user) => user.email === email);
}

export function connectionsFor(userId) {
  return [...identities.values()].filter((row) => row.user_id === userId);
}

function code(person) {
  return `${person.subject}|${person.email}|${person.name}`;
}

function readCode(raw) {
  const parts = String(raw).split("|");
  if (parts.length !== 3 || !parts.every((part) => part.trim())) {
    return null;
  }
  const [subject, email, name] = parts.map((part) => part.trim());
  return { subject, email, name };
}

function userFor(request) {
  const header = request.headers.authorization ?? "";
  if (!header.toLowerCase().startsWith("bearer ")) {
    return null;
  }
  const id = sessions.get(header.slice(7).trim());
  return id ? users.get(id) : null;
}

function issue(user) {
  const token = randomUUID();
  sessions.set(token, user.id);
  return {
    ...user,
    token,
    expires_at: new Date(Date.now() + 30 * 864e5).toISOString(),
  };
}

function asIdentity(row) {
  return {
    provider: row.provider,
    label: LABELS[row.provider] ?? row.provider,
    email: row.email,
    connected_at: row.connected_at,
  };
}

function handle(method, path, body, request, query) {
  if (method === "GET" && path === "/auth/providers") {
    const redirectUri = query.get("redirect_uri") ?? "";
    return {
      status: 200,
      body: providers.map((name) => ({
        name,
        label: LABELS[name],
        // The empty state is not padding: gary-api hands back exactly this
        // for a caller that has not chosen one, and the caller is meant to
        // set it rather than append to it. Leaving it out here let a caller
        // that appended look correct in the specs and carry state twice
        // against a real provider, which refuses to load such a URL at all.
        authorization_url:
          `${BASE_URL}/fake/${name}/authorize` +
          `?redirect_uri=${encodeURIComponent(redirectUri)}&state=`,
      })),
    };
  }

  if (method === "POST" && path === "/auth/sessions") {
    const who = readCode(body.code);
    if (!who) {
      return {
        status: 401,
        body: {
          detail: `Sign in with ${LABELS[body.provider] ?? body.provider}` +
            " did not work, try again",
          code: "provider_refused",
        },
      };
    }

    const key = `${body.provider}:${who.subject}`;
    const held = identities.get(key);
    if (held) {
      return { status: 201, body: issue(users.get(held.user_id)) };
    }

    const user = { id: randomUUID(), email: who.email, display_name: who.name };
    users.set(user.id, user);
    identities.set(key, {
      user_id: user.id,
      email: who.email,
      provider: body.provider,
      connected_at: new Date().toISOString(),
    });
    return { status: 201, body: issue(user) };
  }

  if (method === "DELETE" && path === "/auth/sessions/current") {
    const header = request.headers.authorization ?? "";
    sessions.delete(header.slice(7).trim());
    return { status: 204 };
  }

  const user = userFor(request);

  if (path.startsWith("/auth/me")) {
    if (!user) {
      return { status: 401, body: { detail: "Not signed in" } };
    }
  }

  if (method === "GET" && path === "/auth/me") {
    return { status: 200, body: user };
  }

  if (method === "PATCH" && path === "/auth/me") {
    const name = String(body.display_name ?? "").trim();
    if (!name) {
      return {
        status: 422,
        body: {
          detail: [
            { loc: ["body", "display_name"], msg: "Your display name cannot be blank" },
          ],
        },
      };
    }
    user.display_name = name;
    return { status: 200, body: user };
  }

  if (method === "GET" && path === "/auth/me/identities") {
    return { status: 200, body: connectionsFor(user.id).map(asIdentity) };
  }

  if (method === "POST" && path === "/auth/me/identities") {
    const who = readCode(body.code);
    if (!who) {
      return {
        status: 401,
        body: {
          detail: `Sign in with ${LABELS[body.provider] ?? body.provider}` +
            " did not work, try again",
          code: "provider_refused",
        },
      };
    }

    const key = `${body.provider}:${who.subject}`;
    const held = identities.get(key);
    if (held && held.user_id !== user.id) {
      return {
        status: 409,
        body: {
          detail: `That ${LABELS[body.provider]} account is already connected` +
            " to another gary account",
          code: "identity_taken",
        },
      };
    }

    const row = held ?? {
      user_id: user.id,
      email: who.email,
      provider: body.provider,
      connected_at: new Date().toISOString(),
    };
    identities.set(key, row);
    return { status: 201, body: asIdentity(row) };
  }

  if (method === "DELETE" && path.startsWith("/auth/me/identities/")) {
    const provider = path.slice("/auth/me/identities/".length);
    const mine = connectionsFor(user.id);
    const found = mine.find((row) => row.provider === provider);
    if (!found) {
      return {
        status: 404,
        body: {
          detail: `${LABELS[provider]} is not connected`,
          code: "not_connected",
        },
      };
    }
    if (mine.length === 1) {
      return {
        status: 409,
        body: { detail: "That is your only way to sign in", code: "last_identity" },
      };
    }

    for (const [key, row] of identities) {
      if (row === found) {
        identities.delete(key);
      }
    }
    return { status: 204 };
  }

  // ------------------------------------------------------------- the game

  if (method === "GET" && path === "/catalogue") {
    return { status: 200, body: CATALOGUE };
  }

  if (method === "GET" && path.startsWith("/catalogue/")) {
    const slug = path.slice("/catalogue/".length);
    const found = CATALOGUE.find((one) => one.slug === slug);
    return found
      ? { status: 200, body: found }
      : {
          status: 404,
          body: { detail: "gary does not run that", code: "no_such_system" },
        };
  }

  if (method === "GET" && path === "/models") {
    return { status: 200, body: MODELS };
  }

  if (path.startsWith("/campaigns")) {
    if (!user) {
      return { status: 401, body: { detail: "Not signed in" } };
    }
  }

  if (method === "POST" && path === "/campaigns") {
    if (!String(body.name ?? "").trim()) {
      return {
        status: 422,
        body: {
          detail: [{ loc: ["body", "name"], msg: "A campaign needs a name" }],
        },
      };
    }
    if (!moduleIn(body.system, body.module)) {
      return {
        status: 422,
        body: { detail: "No such module", code: "no_such_module" },
      };
    }
    return {
      status: 201,
      body: asCampaign(addCampaign(user.id, body)),
    };
  }

  if (method === "GET" && path === "/campaigns") {
    return {
      status: 200,
      body: [...campaigns.values()]
        .filter((one) => one.user_id === user.id)
        .sort((a, b) => b.at - a.at)
        .map(asCampaign),
    };
  }

  const inCampaign = path.match(/^\/campaigns\/([^/]+)(\/[a-z]+)?$/);
  if (inCampaign) {
    const campaign = campaigns.get(inCampaign[1]);
    // 404 rather than 403 for someone else's: whether a stranger has a
    // campaign is not yours to learn.
    if (!campaign || campaign.user_id !== user.id) {
      return {
        status: 404,
        body: { detail: "No such campaign", code: "no_such_campaign" },
      };
    }
    const under = inCampaign[2];

    if (method === "GET" && !under) {
      return { status: 200, body: asCampaign(campaign) };
    }

    if (method === "PATCH" && !under) {
      const wanted = body.model ?? null;
      if (wanted !== null && !MODELS.some((one) => one.id === wanted)) {
        return {
          status: 422,
          body: { detail: "gary cannot run on that", code: "unsupported_model" },
        };
      }
      campaign.model = wanted;
      return { status: 200, body: asCampaign(campaign) };
    }

    if (method === "POST" && under === "/characters") {
      if (!String(body.name ?? "").trim()) {
        return {
          status: 422,
          body: {
            detail: [{ loc: ["body", "name"], msg: "A character needs a name" }],
          },
        };
      }
      const made = addCharacterTo(campaign.id, body);
      return {
        status: 201,
        body: {
          id: made.id,
          name: made.name,
          character_class: made.character_class,
          level: made.level,
          max_hp: made.max_hp,
          abilities: made.abilities,
        },
      };
    }

    if (method === "GET" && under === "/world") {
      return {
        status: 200,
        body: {
          place: moduleIn(campaign.system, campaign.module)?.opening ?? "",
          minutes: 0,
          facts: {},
          // Hit points as the world currently has them. Nothing here takes
          // any off, which is gary-api's job and not this one's.
          party: partyOf(campaign.id).map((character) => ({
            id: character.id,
            name: character.name,
            character_class: character.character_class,
            level: character.level,
            hp: character.max_hp,
            max_hp: character.max_hp,
            conditions: [],
            down: false,
          })),
        },
      };
    }

    if (method === "GET" && under === "/turns") {
      return {
        status: 200,
        body: [...turns.values()]
          .filter((one) => one.campaign_id === campaign.id)
          .sort((a, b) => a.at - b.at)
          .map((turn) => ({
            id: turn.id,
            role: turn.role,
            content: turn.content,
            complete: turn.complete,
            rolls: turn.rolls,
          })),
      };
    }
  }

  return { status: 404, body: { detail: "Not found" } };
}

/** A turn, streamed, exactly as gary-api streams one.
 *
 * The frames below have to match what apps/gary-api's own specs assert. They
 * are the contract this stub owes: an event name this invented would render
 * here and vanish in production.
 */
async function stream(request, response, body, campaign) {
  const said = String(body.message ?? "").trim();
  if (!said) {
    response.writeHead(422, { "content-type": "application/json" });
    response.end(
      JSON.stringify({
        detail: [{ loc: ["body", "message"], msg: "Say something" }],
      }),
    );
    return;
  }

  if (partyOf(campaign.id).length === 0) {
    response.writeHead(409, { "content-type": "application/json" });
    response.end(
      JSON.stringify({
        detail: "There is nobody in this campaign to play yet",
        code: "no_party",
      }),
    );
    return;
  }

  // Stored before the stream opens, as gary-api does — what gary is told next
  // time is the transcript, so a turn that only existed on the wire would be
  // a turn the next one is never told about.
  const mine = {
    id: randomUUID(),
    campaign_id: campaign.id,
    role: "player",
    content: said,
    complete: true,
    rolls: [],
    at: turns.size,
  };
  turns.set(mine.id, mine);

  response.writeHead(200, {
    "content-type": "text/event-stream",
    "cache-control": "no-cache",
  });

  // The reader walking away — a scenario ending, a page closing — has to end
  // the turn too, or the writer waits on a gate nobody will open.
  response.on("close", garyFinishes);

  const write = (event, data) =>
    new Promise((resolve) => {
      if (response.writableEnded || response.destroyed) {
        resolve();
        return;
      }
      response.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`, () =>
        // A tick between frames, so what arrives in pieces is rendered in
        // pieces. Without it Node coalesces the writes and the specs would
        // pass against a page that only renders at the end.
        setTimeout(resolve, 5),
      );
    });

  const doing = plan ?? {};
  plan = null;

  if (doing.fail) {
    await write("error", { detail: doing.fail, code: "gm_unavailable" });
    response.end();
    return;
  }

  if (doing.refuse) {
    await write("refusal", { detail: doing.refuse, code: "gm_refused" });
    response.end();
    return;
  }

  const answer = {
    id: randomUUID(),
    campaign_id: campaign.id,
    role: "gm",
    content: "",
    complete: false,
    rolls: [],
    at: turns.size,
  };
  turns.set(answer.id, answer);

  await write("turn", { turn_id: answer.id, role: "gm" });

  if (doing.roll) {
    answer.rolls.push(doing.roll);
    await write("roll", doing.roll);
  }

  const pieces = doing.narration ?? ["The door groans, ", "and gives."];
  for (const piece of pieces) {
    answer.content += piece;
    await write("narration", { text: piece });
  }

  // Held open until the scenario says so. A turn that ended the instant it
  // began could not be asserted on mid-flight, and mid-flight is the only
  // place streaming is distinguishable from not streaming.
  await new Promise((resolve) => {
    release = resolve;
  });

  answer.complete = true;
  await write("done", { turn_id: answer.id, role: "gm" });
  response.end();
}

export async function start() {
  if (server) {
    return;
  }

  server = http.createServer((request, response) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => {
      const raw = Buffer.concat(chunks).toString();
      let body = {};
      try {
        body = raw ? JSON.parse(raw) : {};
      } catch {
        body = {};
      }

      const url = new URL(request.url, BASE_URL);
      const path = url.pathname;

      // gary-web runs in the browser and calls this from the page, so every
      // answer needs the same welcome gary-api gives — without it the browser
      // makes the call and then refuses to hand back the result, and the
      // scenario sees an app that renders nothing for no stated reason.
      const origin = request.headers.origin;
      if (origin) {
        response.setHeader("access-control-allow-origin", origin);
        response.setHeader("vary", "origin");
      }

      // The preflight. A POST carrying JSON is not a request a browser makes
      // without asking first.
      if (request.method === "OPTIONS") {
        response.writeHead(204, {
          "access-control-allow-methods": "GET,POST,PATCH,DELETE,OPTIONS",
          "access-control-allow-headers": "authorization,content-type,x-request-id",
        });
        response.end();
        return;
      }

      // The provider half. A real one shows a consent screen; this one has
      // nothing to ask, so it bounces straight back with the code for
      // whoever the scenario said would be there.
      const authorizing = path.match(/^\/fake\/([a-z]+)\/authorize$/);
      if (authorizing) {
        const provider = authorizing[1];

        // As Facebook does: a URL carrying state twice is refused outright,
        // not read leniently. Without this the double is invisible here.
        if (url.searchParams.getAll("state").length > 1) {
          response.writeHead(400, { "content-type": "text/plain" });
          response.end("Can't load URL: state given more than once");
          return;
        }

        const back = new URL(url.searchParams.get("redirect_uri"));
        const person = waiting.get(provider);
        if (person) {
          back.searchParams.set("code", code(person));
        } else {
          // Nobody arranged. A provider that will not say who you are is a
          // real outcome, and the specs get it by not asking for anyone.
          back.searchParams.set("error", "access_denied");
        }
        back.searchParams.set("state", url.searchParams.get("state") ?? provider);

        // Facebook appends this to every redirect it makes. Nothing reads it
        // and nothing breaks on it, but it rides along into the page unless
        // the callback drops it, so the double does it too.
        if (provider === "facebook") {
          back.hash = "_=_";
        }
        response.writeHead(302, { location: back.toString() });
        response.end();
        return;
      }

      if (answeringWithGarbage) {
        // 200 on purpose: a non-200 is a case callApi already handles. What
        // this reproduces is a success that cannot be parsed.
        response.writeHead(200, { "content-type": "application/json" });
        response.end("<html><body>502 Bad Gateway</body></html>");
        return;
      }

      // Taken before handle(), which answers with a whole body — a turn is
      // the one thing here that writes as it goes.
      const playing = path.match(/^\/campaigns\/([^/]+)\/turns$/);
      if (request.method === "POST" && playing) {
        const who = userFor(request);
        const campaign = campaigns.get(playing[1]);
        if (!who) {
          response.writeHead(401, { "content-type": "application/json" });
          response.end(JSON.stringify({ detail: "Not signed in" }));
        } else if (!campaign || campaign.user_id !== who.id) {
          response.writeHead(404, { "content-type": "application/json" });
          response.end(
            JSON.stringify({
              detail: "No such campaign",
              code: "no_such_campaign",
            }),
          );
        } else {
          void stream(request, response, body, campaign);
        }
        return;
      }

      const result = handle(request.method, path, body, request, url.searchParams);

      if (result.body === undefined) {
        response.writeHead(result.status);
        response.end();
        return;
      }

      response.writeHead(result.status, { "content-type": "application/json" });
      response.end(JSON.stringify(result.body));
    });
  });

  await new Promise((resolve) => server.listen(PORT, "127.0.0.1", resolve));
}

export async function stop() {
  if (!server) {
    return;
  }

  const closing = server;
  server = null;
  await new Promise((resolve) => closing.close(resolve));
}
