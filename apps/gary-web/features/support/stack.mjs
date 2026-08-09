import { spawn, execFileSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

// Boots the real gary-api against a throwaway database, for the @fullstack
// scenarios. Everything else runs against the in-memory stub, which is fast
// but agrees with whatever we told it to say — these scenarios are the ones
// that would notice gary-api disagreeing.

const API_DIR = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../../gary-api",
);

export const API_PORT = 8798;
export const API_URL = `http://127.0.0.1:${API_PORT}`;

let api = null;
let database = null;
let log = "";

function uv(args, env = {}) {
  return execFileSync("uv", ["run", ...args], {
    cwd: API_DIR,
    encoding: "utf8",
    env: { ...process.env, ...env },
  }).trim();
}

async function waitForHealth(timeoutMs) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${API_URL}/health`);
      if (response.ok) {
        return;
      }
    } catch {
      // Not up yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  throw new Error(`gary-api did not come up within ${timeoutMs}ms:\n${log}`);
}

export async function start() {
  database = `gary_e2e_${randomBytes(4).toString("hex")}`;
  const url = uv(["python", "e2e_db.py", "create", database]);

  // Through the real migrations, not metadata.create_all — a schema the
  // migrations cannot produce is a schema that will not deploy.
  uv(["alembic", "upgrade", "head"], { DATABASE_URL: url });

  api = spawn(
    "uv",
    ["run", "uvicorn", "gary_api.app:app", "--host", "127.0.0.1", "--port", String(API_PORT)],
    {
      cwd: API_DIR,
      env: {
        ...process.env,
        DATABASE_URL: url,
        // Pinned: a RESEND_API_KEY in the environment would otherwise make
        // an e2e run send real email, and the console provider is how these
        // scenarios read the reset link.
        MAIL_PROVIDER: "console",
        // Python block-buffers stdout into a pipe, so its output can sit
        // unflushed for as long as it takes to fill 8KB — long enough for a
        // step to read an empty log and conclude nothing was sent.
        PYTHONUNBUFFERED: "1",
        WEB_BASE_URL: `http://localhost:3999`,
      },
    },
  );

  const collect = (chunk) => {
    log += chunk.toString();
  };
  api.stdout.on("data", collect);
  api.stderr.on("data", collect);

  await waitForHealth(60_000);
}

export function reset() {
  log = "";
  uv(["python", "e2e_db.py", "reset", database]);
}

/** Everything gary-api has written since the last scenario began. */
export function apiOutput() {
  return log;
}

/** The token from the most recent reset link gary-api logged. */
export function emailedResetToken() {
  const found = [...log.matchAll(/[?&]token=([\w-]+)/g)];
  if (found.length === 0) {
    throw new Error(
      `gary-api logged no reset link in ${log.length} bytes of output:\n${log}`,
    );
  }
  return found.at(-1)[1];
}

export async function stop() {
  api?.kill();
  api = null;

  if (database) {
    uv(["python", "e2e_db.py", "drop", database]);
    database = null;
  }
}
