import http from "node:http";
import { randomUUID } from "node:crypto";

// A stand-in for gary-api, holding accounts and sessions in memory. It exists
// so the browser specs can drive real sign-in flows without a Postgres.
//
// It owes gary-api a contract, not an implementation: statuses and bodies
// here must match what apps/gary-api's own specs assert, or these specs pass
// against a service that does not exist.

const PORT = 8799;
const MINIMUM_PASSWORD = 8;

export const BASE_URL = `http://127.0.0.1:${PORT}`;

let server = null;
const users = new Map(); // email -> {id, email, display_name, password}
const sessions = new Map(); // token -> email
const resets = new Map(); // token -> {email, used, expired}
const verifications = new Map(); // token -> {email, used, expired}

export function reset() {
  users.clear();
  sessions.clear();
  resets.clear();
  verifications.clear();
}

export function addUser(email, displayName, password, { verified = false } = {}) {
  const key = email.toLowerCase();
  users.set(key, {
    id: randomUUID(),
    email: key,
    display_name: displayName,
    password,
    email_verified: verified,
  });
  if (!verified) {
    issueVerification(key);
  }
}

function issueVerification(email) {
  const token = randomUUID();
  verifications.set(token, { email, used: false, expired: false });
  return token;
}

export function hasUser(email) {
  return users.has(email.toLowerCase());
}

export function verifyUser(email) {
  users.get(email.toLowerCase()).email_verified = true;
}

export function lastVerificationToken() {
  const live = [...verifications.entries()].filter(([, v]) => !v.used);
  return live.length ? live[live.length - 1][0] : null;
}

export function expireVerification(token) {
  const found = verifications.get(token);
  if (found) {
    found.expired = true;
  }
}

export function markVerificationUsed(token) {
  const found = verifications.get(token);
  if (found) {
    found.used = true;
    users.get(found.email).email_verified = true;
  }
}

export function lastResetToken() {
  const live = [...resets.entries()].filter(([, value]) => !value.used);
  return live.length ? live[live.length - 1][0] : null;
}

export function expireReset(token) {
  const found = resets.get(token);
  if (found) {
    found.expired = true;
  }
}

export function markResetUsed(token, newPassword) {
  const found = resets.get(token);
  if (found) {
    found.used = true;
    users.get(found.email).password = newPassword;
  }
}

function publicUser(user) {
  return {
    id: user.id,
    email: user.email,
    display_name: user.display_name,
    email_verified: user.email_verified,
  };
}

function bearer(request) {
  const header = request.headers.authorization ?? "";
  if (!header.toLowerCase().startsWith("bearer ")) {
    return null;
  }
  return sessions.get(header.slice(7).trim()) ?? null;
}

function issue(email) {
  const token = randomUUID();
  sessions.set(token, email);
  const expires = new Date(Date.now() + 30 * 24 * 3600 * 1000);
  return { token, expires_at: expires.toISOString() };
}

function invalid(field, message) {
  return { status: 422, body: { detail: [{ loc: ["body", field], msg: message }] } };
}

function handle(method, path, body, request) {
  if (method === "POST" && path === "/auth/register") {
    if (!body.email?.includes("@")) return invalid("email", "not an email");
    if ((body.password ?? "").length < MINIMUM_PASSWORD)
      return invalid("password", "too short");
    if (!body.display_name?.trim()) return invalid("display_name", "blank");

    const key = body.email.toLowerCase();
    if (users.has(key)) {
      return { status: 409, body: { detail: "That email address is already registered" } };
    }

    addUser(key, body.display_name.trim(), body.password);
    return { status: 201, body: { ...publicUser(users.get(key)), ...issue(key) } };
  }

  if (method === "POST" && path === "/auth/sessions") {
    const user = users.get((body.email ?? "").toLowerCase());
    if (!user || user.password !== body.password) {
      return { status: 401, body: { detail: "Invalid email or password" } };
    }
    return { status: 201, body: { ...publicUser(user), ...issue(user.email) } };
  }

  if (method === "DELETE" && path === "/auth/sessions/current") {
    const header = request.headers.authorization ?? "";
    sessions.delete(header.slice(7).trim());
    return { status: 204 };
  }

  const email = bearer(request);

  if (method === "GET" && path === "/auth/me") {
    if (!email) return { status: 401, body: { detail: "Not signed in" } };
    return { status: 200, body: publicUser(users.get(email)) };
  }

  if (method === "PATCH" && path === "/auth/me") {
    if (!email) return { status: 401, body: { detail: "Not signed in" } };
    if (!body.display_name?.trim()) return invalid("display_name", "blank");

    users.get(email).display_name = body.display_name.trim();
    return { status: 200, body: publicUser(users.get(email)) };
  }

  if (method === "POST" && path === "/auth/me/password") {
    if (!email) return { status: 401, body: { detail: "Not signed in" } };
    const user = users.get(email);
    if (user.password !== body.current_password) {
      return { status: 403, body: { detail: "That is not your current password" } };
    }
    if ((body.new_password ?? "").length < MINIMUM_PASSWORD)
      return invalid("new_password", "too short");

    user.password = body.new_password;
    return { status: 204 };
  }

  if (method === "POST" && path === "/auth/verify-email") {
    const found = verifications.get(body.token);
    if (!found || found.used || found.expired) {
      return {
        status: 400,
        body: {
          detail: "That verification link has expired or has already been used",
        },
      };
    }
    markVerificationUsed(body.token);
    return { status: 204 };
  }

  if (method === "POST" && path === "/auth/verify-email/resend") {
    if (!email) return { status: 401, body: { detail: "Not signed in" } };
    if (!users.get(email).email_verified) {
      issueVerification(email);
    }
    return { status: 204, status_override: 202 };
  }

  if (method === "POST" && path === "/auth/password-reset") {
    const key = (body.email ?? "").toLowerCase();
    if (users.has(key)) {
      resets.set(randomUUID(), { email: key, used: false, expired: false });
    }
    // 202 either way: whether the address is known is not answerable here.
    return { status: 204, status_override: 202 };
  }

  if (method === "GET" && path.startsWith("/auth/password-reset/")) {
    const token = decodeURIComponent(path.slice("/auth/password-reset/".length));
    const found = resets.get(token);
    if (!found || found.used || found.expired) {
      return {
        status: 400,
        body: { detail: "That reset link has expired or has already been used" },
      };
    }
    return { status: 204 };
  }

  if (method === "POST" && path === "/auth/password-reset/confirm") {
    const found = resets.get(body.token);
    if (!found || found.used || found.expired) {
      return {
        status: 400,
        body: { detail: "That reset link has expired or has already been used" },
      };
    }
    if ((body.new_password ?? "").length < MINIMUM_PASSWORD)
      return invalid("new_password", "too short");

    markResetUsed(body.token, body.new_password);
    return { status: 204 };
  }

  return { status: 404 };
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

      const path = request.url.split("?")[0];
      const result = handle(request.method, path, body, request);
      const status = result.status_override ?? result.status;

      if (result.body === undefined) {
        response.writeHead(status);
        response.end();
        return;
      }

      response.writeHead(status, { "content-type": "application/json" });
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
