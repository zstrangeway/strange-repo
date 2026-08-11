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

/** Where the specs serve gary-web, which is what a browser will call from. */
const WEB_ORIGIN = "http://localhost:3999";

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
        // The stand-in for Google, Facebook and Apple. Reaching the real
        // three would mean driving their consent screens by hand.
        IDENTITY_FAKE: "1",
        // And the stand-in for the model, on the same argument: a real one
        // costs money, answers differently every time, and is not what these
        // scenarios are here to check. The engines under it are all real.
        GM_FAKE: "1",
        // Emptied rather than inherited. With a key, gary asks OpenRouter
        // what it serves and the list becomes whatever OpenRouter is serving
        // today — which is a suite that passes or fails on somebody else's
        // catalogue. Without one, it offers the built-in list.
        OPENROUTER_API_KEY: "",
        // Deterministic dice, so a spec can assert a number rather than only
        // that a number arrived.
        DICE_SEED: "7",
        // Where its own stand-in consent page lives, as the browser will
        // reach it — the default assumes port 8000 and this is not that.
        API_BASE_URL: API_URL,
        // Python block-buffers stdout into a pipe, so its output can sit
        // unflushed for as long as it takes to fill 8KB — long enough for a
        // step to read an empty log and conclude nothing was sent.
        PYTHONUNBUFFERED: "1",
        // gary-web calls this from the page, so its origin has to be named
        // here or the browser makes every request and then refuses to hand
        // back the answer. The default is port 3000; the specs are not on it.
        BROWSER_ORIGINS: WEB_ORIGIN,
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
