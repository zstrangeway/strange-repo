// Structured logging, in the same shape gary-api emits. One JSON object per
// line, so one search finds a single user's action in both apps' logs:
//
//   {"timestamp":"2026-08-09T17:50:00.123Z","level":"error","logger":"api",
//    "message":"api.unreachable","app":"gary-web","request_id":"5f2c…",
//    "error":{"type":"TypeError","message":"fetch failed","stack":"…"}}
//
// This is server-side only. Every caller is a Server Component, a Server
// Action or middleware — none of it runs in the browser, and none of it
// shows up in devtools.

import { AsyncLocalStorage } from "node:async_hooks";
import { randomUUID } from "node:crypto";

export const APP = "gary-web";
export const REQUEST_ID_HEADER = "x-request-id";

const LEVELS = { debug: 10, info: 20, warning: 30, error: 40 } as const;
export type Level = keyof typeof LEVELS;

export type Fields = Record<string, unknown>;

// The formatter owns these. A caller passing one gets it renamed with a
// trailing underscore rather than overwriting it — the same rule gary-api
// applies, so a line means the same thing whichever app wrote it.
const RESERVED = new Set(["timestamp", "level", "logger", "message", "app"]);

const store = new AsyncLocalStorage<Fields>();

function floor(): number {
  // Read per call rather than at module load: LOG_LEVEL comes from the
  // deployment, and the value at build time is not it.
  const configured = (process.env.LOG_LEVEL ?? "").toLowerCase();
  return configured in LEVELS ? LEVELS[configured as Level] : LEVELS.info;
}

function timestamp(): string {
  // toISOString is already UTC with milliseconds, which is the contract.
  return new Date().toISOString().replace(/(\.\d{3})\d*Z$/, "$1Z");
}

function shapeError(error: Error): Fields {
  return { type: error.name, message: error.message, stack: error.stack ?? "" };
}

/** Anything JSON cannot hold natively, rendered rather than thrown away. */
function render(_key: string, value: unknown): unknown {
  if (value instanceof Error) {
    return shapeError(value);
  }
  if (typeof value === "bigint") {
    return value.toString();
  }
  if (typeof value === "function" || typeof value === "symbol") {
    return String(value);
  }
  return value;
}

function merge(into: Fields, fields: Fields): void {
  for (const [key, value] of Object.entries(fields)) {
    into[RESERVED.has(key) ? `${key}_` : key] = value;
  }
}

export function write(level: Level, logger: string, message: string, fields: Fields = {}): void {
  if (LEVELS[level] < floor()) {
    return;
  }

  const core: Fields = {
    timestamp: timestamp(),
    level,
    logger,
    message,
    app: APP,
  };
  const payload: Fields = { ...core };
  merge(payload, store.getStore() ?? {});
  merge(payload, fields);

  let line: string;
  try {
    line = JSON.stringify(payload, render);
  } catch (error) {
    // A circular field is not worth losing the line over, and it is
    // certainly not worth throwing from inside a log call. The fields go,
    // the line stays, and it says which of the two happened. Rebuilt from
    // `core` rather than from `payload`, which still holds whatever it was
    // that could not be serialised a moment ago.
    line = JSON.stringify({
      ...core,
      fields_unserialisable: error instanceof Error ? error.message : String(error),
    });
  }

  // warning and error to stderr, the rest to stdout — the split every log
  // collector already understands.
  const sink = LEVELS[level] >= LEVELS.warning ? process.stderr : process.stdout;
  sink.write(`${line}\n`);
}

export type Logger = {
  debug(message: string, fields?: Fields): void;
  info(message: string, fields?: Fields): void;
  warning(message: string, fields?: Fields): void;
  error(message: string, fields?: Fields): void;
};

export function getLogger(name: string): Logger {
  return {
    debug: (message, fields) => write("debug", name, message, fields),
    info: (message, fields) => write("info", name, message, fields),
    warning: (message, fields) => write("warning", name, message, fields),
    error: (message, fields) => write("error", name, message, fields),
  };
}

/** The fields currently bound. Empty outside a bound block. */
export function context(): Fields {
  return { ...(store.getStore() ?? {}) };
}

/** Add fields to every line logged inside `run`, however deep. */
export function withContext<T>(fields: Fields, run: () => T): T {
  return store.run({ ...(store.getStore() ?? {}), ...fields }, run);
}

export function newRequestId(): string {
  return randomUUID();
}

/**
 * The id for the work in flight, minting one if nothing bound it.
 *
 * The fallback matters: a page that forgets to establish a context still
 * gets a line that correlates with gary-api's, rather than one with no id
 * at all. It only costs the grouping of several calls under one id.
 */
export function requestId(): string {
  const bound = store.getStore()?.request_id;
  return typeof bound === "string" ? bound : newRequestId();
}
