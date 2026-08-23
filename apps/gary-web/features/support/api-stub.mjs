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
const turns = new Map(); // id -> {id, campaign_id, scene_id, role, content, ...}
const scenes = new Map(); // id -> {id, campaign_id, number, title, recap, open}

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
const METHOD = {
  "standard-array": {
    slug: "standard-array",
    name: "The standard array",
    blurb: "15, 14, 13, 12, 10, 8 — put them where you like.",
    generates: true,
    arrange: true,
  },
  "roll-4d6-drop-lowest": {
    slug: "roll-4d6-drop-lowest",
    name: "Roll 4d6, drop the lowest",
    blurb: "Six sets of four dice, worst of each thrown away.",
    generates: true,
    arrange: true,
  },
  "point-buy": {
    slug: "point-buy",
    name: "Point buy",
    blurb: "Spend a budget on scores.",
    generates: false,
    arrange: true,
  },
  manual: {
    slug: "manual",
    name: "Type them in",
    blurb: "Enter six scores you worked out somewhere else.",
    generates: false,
    arrange: true,
  },
};

const CATALOGUE = [
  {
    slug: "dnd-5e",
    name: "Dungeons & Dragons 5th Edition",
    blurb: "Roll a d20, add a modifier, meet a difficulty class.",
    // A subset of gary-api's twelve, and every one of them has to be in it —
    // a class this stub invented would let a scenario pass against a service
    // that refuses it.
    classes: ["cleric", "fighter", "rogue", "wizard"],
    abilities: ["str", "dex", "con"],
    degrees: ["success", "failure"],
    // Owed to gary-api's own list, slug for slug. A method this stub invented
    // would let a scenario pass against a service that refuses it.
    methods: [
      METHOD["standard-array"],
      METHOD["roll-4d6-drop-lowest"],
      METHOD["point-buy"],
      METHOD.manual,
    ],
    cannot_generate: "",
    scores: [3, 18],
    point_costs: { 8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9 },
    point_budget: 27,
    // Owed to gary-api's own table, for the classes this stub offers. A
    // system that names no hit dice — Pathfinder, below — falls back to the
    // default, which is what gary-api does with one it has no die for.
    hit_dice: { cleric: 8, fighter: 10, rogue: 8, wizard: 6 },
    // Owed to gary-api's own advancement table, level 1 first. Short of its
    // twenty on purpose: a scenario here proves the card reads a number it
    // was given, and where the number comes from is settled by gary-api's
    // specs. A system that prices no level leaves this out, as add-1e does.
    experience_table: [0, 300, 900, 2700, 6500],
    modules: [
      {
        slug: "the-drowned-belfry",
        title: "The Drowned Belfry",
        premise: "A bell tower sunk to its eaves in the marsh outside Ashfen.",
        hook: "Ashfen's reeve is paying you to stop the ringing before dark tomorrow.",
        opening: "the causeway into Ashfen marsh, at dusk",
      },
      {
        slug: "the-ashfen-road",
        title: "The Ashfen Road",
        premise: "Three carters gone on a road with nowhere to hide.",
        hook: "The carters' guild will pay for its drivers found, before the next convoy leaves.",
        opening: "the last waystation before the missing stretch of road",
      },
    ],
  },
  {
    slug: "pathfinder-2e",
    name: "Pathfinder 2nd Edition",
    blurb: "Four degrees of success, and a natural 20 shifts the ladder.",
    classes: ["fighter", "rogue"],
    abilities: ["str", "dex", "con"],
    // Pathfinder generates nothing: its scores come from ancestry and
    // background boosts, and typing them in is the only way through.
    methods: [METHOD.manual],
    cannot_generate:
      "Pathfinder scores come from ancestry, background and class boosts " +
      "rather than dice. Work them out and type them in.",
    scores: [3, 18],
    point_costs: {},
    point_budget: 0,
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
        hook: "The harbourmaster is losing a berth a week and has hired you to find why.",
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
  scenes.clear();
  providers = ["google", "facebook", "apple"];
  answeringWithGarbage = false;
  plan = null;
  fighting = null;
  // Let go of anything still held, or the scenario that held it leaves a
  // socket open and the next one waits on it.
  garyFinishes();
}

/** What gary will do with the next thing said to it. */
export function garyWill(next) {
  plan = next;
}

// A fight, when a scenario wants one on screen. One monster, because what the
// browser has to render is an order and a position in it, and a second would
// only make the fixture longer.
const FOE = {
  id: "foe-1",
  name: "mud creature",
  hp: 8,
  max_hp: 11,
  armour_class: 13,
  conditions: [],
  down: false,
};

let fighting = null;

/** Put a fight on, with the order sitting on whoever the scenario names. */
export function fightUnderway(at = 0, round = 1) {
  fighting = { at, round };
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

/** The third-edition-onward formula, which 5e and Pathfinder kept. */
function modifierFor(score) {
  return Math.floor((score - 10) / 2);
}

/**
 * The hit die at full plus the constitution modifier, never below one — the
 * same sum gary-api makes, because a stub that handed back a flat eight would
 * let a scenario about hit points following from a sheet pass against a
 * service where they do.
 */
function hitPointsFor(system, characterClass, abilities) {
  const die = system?.hit_dice?.[characterClass];
  if (die === undefined) return DEFAULT_HP;
  return Math.max(1, die + modifierFor(abilities.con));
}

/**
 * What the next level costs, or null when there is no next number to reach.
 *
 * The same two silences gary-api answers alike: the top of a table, and a
 * system with no table at all.
 */
function nextLevelFor(systemSlug, level) {
  const table = CATALOGUE.find((one) => one.slug === systemSlug)
    ?.experience_table;
  if (!table) return null;
  return level < table.length ? table[level] : null;
}

export function addCharacterTo(
  campaignId,
  { name, character_class, mine, abilities },
) {
  const campaign = campaigns.get(campaignId);
  const system = CATALOGUE.find((one) => one.slug === campaign?.system);
  // Whatever was placed, over the system's default of ten for the rest.
  const sheet = { str: 10, dex: 10, con: 10, ...(abilities ?? {}) };

  const character = {
    id: randomUUID(),
    campaign_id: campaignId,
    name,
    character_class,
    played_by: mine ? "player" : "gary",
    level: 1,
    // Where they started. gary-api sets this from what the level costs; a
    // character made here is always level 1, which costs nothing anywhere.
    experience: 0,
    max_hp: hitPointsFor(system, character_class, sheet),
    abilities: sheet,
    at: characters.size,
  };
  characters.set(character.id, character);
  return character;
}

/** The scene a campaign is playing, opening its first if it has none — the
 *  same lazy opening gary-api does, and for the same reason. */
function openScene(campaignId) {
  const found = [...scenes.values()].find(
    (one) => one.campaign_id === campaignId && one.open,
  );
  if (found) {
    return found;
  }

  const scene = {
    id: randomUUID(),
    campaign_id: campaignId,
    number:
      [...scenes.values()].filter((one) => one.campaign_id === campaignId)
        .length + 1,
    title: "",
    recap: null,
    open: true,
  };
  scenes.set(scene.id, scene);
  return scene;
}

/** End the scene being played and open the next. The recap stands in for what
 *  a model would have written — gary-api's close pass is a model call, and
 *  this owes it the shape rather than the sentence. */
function breakScene(campaignId, title) {
  const closing = openScene(campaignId);
  const said = [...turns.values()].filter((one) => one.scene_id === closing.id);
  closing.open = false;
  closing.recap = said.length
    ? `Previously: ${said.map((one) => one.content).join(" ")}`
    : null;
  const opened = openScene(campaignId);
  opened.title = title;
  return opened;
}

/** Whoever the player is at this table, if anybody is yet. */
export function playedBy(campaignId) {
  return playing(campaignId);
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
    premise: moduleIn(campaign.system, campaign.module)?.premise ?? "",
    hook: moduleIn(campaign.system, campaign.module)?.hook ?? "",
    place: moduleIn(campaign.system, campaign.module)?.opening ?? "",
    turns: [...turns.values()].filter((one) => one.campaign_id === campaign.id)
      .length,
    begun: [...turns.values()].some((one) => one.campaign_id === campaign.id),
    // Resolved, never null — a client should not have to know what the
    // deployment's default is to render which model a campaign runs on.
    model: campaign.model ?? FALLBACK_MODEL,
    model_chosen: campaign.model !== null,
  };
}

function playing(campaignId) {
  return partyOf(campaignId).find((one) => one.played_by === "player");
}

function asCharacter(character) {
  return {
    id: character.id,
    name: character.name,
    character_class: character.character_class,
    level: character.level,
    experience: character.experience,
    max_hp: character.max_hp,
    abilities: character.abilities,
    played_by: character.played_by,
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

  const takingOver = path.match(
    /^\/campaigns\/([^/]+)\/characters\/([^/]+)\/player$/,
  );
  if (method === "POST" && takingOver) {
    const campaign = campaigns.get(takingOver[1]);
    if (!campaign || campaign.user_id !== user.id) {
      return {
        status: 404,
        body: { detail: "No such campaign", code: "no_such_campaign" },
      };
    }
    const here = partyOf(campaign.id);
    const wanted = here.find((one) => one.id === takingOver[2]);
    if (!wanted) {
      return {
        status: 404,
        body: {
          detail: "No such character in this campaign",
          code: "no_such_character",
        },
      };
    }
    for (const character of here) {
      character.played_by = character === wanted ? "player" : "gary";
    }
    return { status: 200, body: here.map(asCharacter) };
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
      if (body.mine && playing(campaign.id)) {
        return {
          status: 409,
          body: {
            detail: "You are already playing somebody in this campaign",
            code: "already_playing",
          },
        };
      }
      const system = CATALOGUE.find((one) => one.slug === campaign.system);
      const [low, high] = system?.scores ?? [3, 18];
      for (const [ability, score] of Object.entries(body.abilities ?? {})) {
        // The same two refusals gary-api makes, because this stub owes it a
        // contract: an ability the system does not have, and a score outside
        // what it allows.
        if (!system?.abilities.includes(ability)) {
          return {
            status: 422,
            body: {
              detail: `'${ability}' is not an ability in this system`,
              code: "no_such_ability",
            },
          };
        }
        if (score < low || score > high) {
          return {
            status: 422,
            body: {
              detail: `a score in this system is between ${low} and ${high}`,
              code: "bad_score",
            },
          };
        }
      }

      const made = addCharacterTo(campaign.id, body);
      return { status: 201, body: asCharacter(made) };
    }

    if (method === "POST" && under === "/scores") {
      const system = CATALOGUE.find((one) => one.slug === campaign.system);
      const wanted = system?.methods.find((one) => one.slug === body.method);
      if (!wanted?.generates) {
        return {
          status: 422,
          body: {
            detail: `${campaign.system} does not generate ${body.method}`,
            code: "no_such_method",
          },
        };
      }

      // Rolled here rather than fixed, because a scenario asserts that two
      // draws differ — a stub handing back the same six numbers twice would
      // agree with a client that cached the first set.
      const scores = system.abilities.map(() => {
        if (wanted.slug === "standard-array") {
          return { score: 12, dice: [], dropped: null };
        }
        const dice = [0, 0, 0, 0].map(
          () => 1 + Math.floor(Math.random() * 6),
        );
        const dropped = Math.min(...dice);
        return {
          score: dice.reduce((a, b) => a + b, 0) - dropped,
          dice,
          dropped,
        };
      });

      return {
        status: 200,
        body: {
          method: wanted.slug,
          scores,
          assigned: wanted.arrange
            ? null
            : Object.fromEntries(
                system.abilities.map((one, at) => [one, scores[at].score]),
              ),
        },
      };
    }

    if (method === "GET" && under === "/characters") {
      return { status: 200, body: partyOf(campaign.id).map(asCharacter) };
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
            experience: character.experience,
            // What the next level costs. Counted the way gary-api counts it
            // rather than hardcoded, so a scenario that advances somebody
            // gets a card that moves with them.
            next_level: nextLevelFor(campaign.system, character.level),
            hp: character.max_hp,
            max_hp: character.max_hp,
            conditions: [],
            down: false,
            played_by: character.played_by,
          })),
          enemies: fighting ? [FOE] : [],
          // A fight, when a scenario asked for one. Arranged rather than
          // simulated: what the browser has to prove is that it renders the
          // order and whose turn it is, and gary-api's own specs are where
          // the order being right is settled.
          fight: fighting
            ? {
                order: [
                  ...partyOf(campaign.id).map((character) => ({
                    id: character.id,
                    name: character.name,
                    side: "party",
                  })),
                  { id: FOE.id, name: FOE.name, side: "adversary" },
                ],
                at: fighting.at,
                round: fighting.round,
              }
            : null,
        },
      };
    }

    if (method === "GET" && under === "/scenes") {
      openScene(campaign.id);
      return {
        status: 200,
        body: [...scenes.values()]
          .filter((one) => one.campaign_id === campaign.id)
          .sort((a, b) => a.number - b.number)
          .map((one) => ({
            id: one.id,
            number: one.number,
            title: one.title,
            recap: one.recap,
            open: one.open,
          })),
      };
    }

    if (method === "POST" && under === "/scenes") {
      if (partyOf(campaign.id).length === 0) {
        return {
          status: 409,
          body: {
            detail: "There is nobody in this campaign to play yet",
            code: "no_party",
          },
        };
      }
      const opened = breakScene(campaign.id, String(body.title ?? ""));
      return {
        status: 201,
        body: {
          id: opened.id,
          number: opened.number,
          title: opened.title,
          recap: opened.recap,
          open: opened.open,
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
            scene_id: turn.scene_id,
            rolls: turn.rolls,
            changes: turn.changes ?? [],
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
async function stream(request, response, body, campaign, opening = false) {
  // An opening answers no message — that is the only thing unusual about it.
  const said = opening ? "" : String(body.message ?? "").trim();
  if (!opening && !said) {
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
  if (!playing(campaign.id)) {
    response.writeHead(409, { "content-type": "application/json" });
    response.end(
      JSON.stringify({
        detail: "None of these characters is yours to play",
        code: "no_character",
      }),
    );
    return;
  }

  // Stored before the stream opens, as gary-api does — what gary is told next
  // time is the transcript, so a turn that only existed on the wire would be
  // a turn the next one is never told about.
  const scene = openScene(campaign.id);
  if (!opening) {
    const mine = {
      id: randomUUID(),
      campaign_id: campaign.id,
      scene_id: scene.id,
      role: "player",
      content: said,
      complete: true,
      rolls: [],
      at: turns.size,
    };
    turns.set(mine.id, mine);
  }

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
    scene_id: scene.id,
    role: "gm",
    content: "",
    complete: false,
    rolls: [],
    changes: [],
    at: turns.size,
  };
  turns.set(answer.id, answer);

  await write("turn", { turn_id: answer.id, role: "gm" });

  if (doing.roll) {
    answer.rolls.push(doing.roll);
    await write("roll", doing.roll);
  }

  // An award, and whatever the engine did about it. Both are frames on the
  // open stream and both are kept on the turn, because gary-api sends them
  // that way and a reload gets them back from the transcript.
  //
  // The level is worked out here rather than dictated by the scenario, so a
  // scenario that awards enough gets a level for the same reason it would
  // against gary-api — but the table is the one above, kept short, and where
  // the number comes from is settled by gary-api's own specs.
  if (doing.award) {
    const { who, amount, reason = "the mud creature" } = doing.award;
    const character = partyOf(campaign.id).find((one) => one.name === who);
    if (character) {
      character.experience += amount;
      const earned = { kind: "experience-gained", character: who, amount, reason };
      answer.changes.push(earned);
      await write("world", earned);

      const table =
        CATALOGUE.find((one) => one.slug === campaign.system)
          ?.experience_table ?? [];
      let reached = 1;
      table.forEach((needed, at) => {
        if (character.experience >= needed) reached = at + 1;
      });
      while (character.level < reached) {
        character.level += 1;
        // The engine's die. Fixed here because a browser spec asserting on a
        // random number would be a spec that fails one run in six.
        const gained = 5;
        character.max_hp += gained;
        const levelled = {
          kind: "level-gained",
          character: who,
          level: character.level,
          hit_points: gained,
        };
        answer.changes.push(levelled);
        await write("world", levelled);
      }
    }
  }

  const pieces =
    doing.narration ??
    (opening
      ? ["The causeway runs out into the marsh, ", "and the bell is ringing."]
      : ["The door groans, ", "and gives."]);
  for (const piece of pieces) {
    answer.content += piece;
    await write("narration", { text: piece });
  }

  // Held open until the scenario says so. A turn that ended the instant it
  // began could not be asserted on mid-flight, and mid-flight is the only
  // place streaming is distinguishable from not streaming.
  //
  // Except an opening, which nobody asked for and no scenario watches
  // mid-flight. Holding one would leave the composer occupied from the
  // moment the page loads, and every step after that waiting on a turn
  // gary was never going to finish.
  if (!opening) {
    await new Promise((resolve) => {
      release = resolve;
    });
  }

  // Gary asking for a break: acted on once the turn is over, as gary-api
  // does it, and relayed on the same open stream.
  if (doing.scene) {
    const opened = breakScene(campaign.id, doing.scene);
    await write("scene", {
      scene_id: opened.id,
      title: opened.title,
      number: opened.number,
    });
  }

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
      const playing = path.match(/^\/campaigns\/([^/]+)\/(turns|opening)$/);
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
        } else if (
          playing[2] === "opening" &&
          [...turns.values()].some((one) => one.campaign_id === campaign.id)
        ) {
          response.writeHead(409, { "content-type": "application/json" });
          response.end(
            JSON.stringify({
              detail: "This campaign has already begun",
              code: "already_begun",
            }),
          );
        } else {
          void stream(request, response, body, campaign, playing[2] === "opening");
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
