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

export function answerWithGarbage() {
  answeringWithGarbage = true;
}

export function reset() {
  users.clear();
  identities.clear();
  sessions.clear();
  waiting.clear();
  providers = ["google", "facebook", "apple"];
  answeringWithGarbage = false;
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
      return { status: 404, body: { detail: `${LABELS[provider]} is not connected` } };
    }
    if (mine.length === 1) {
      return { status: 409, body: { detail: "That is your only way to sign in" } };
    }

    for (const [key, row] of identities) {
      if (row === found) {
        identities.delete(key);
      }
    }
    return { status: 204 };
  }

  return { status: 404, body: { detail: "Not found" } };
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
