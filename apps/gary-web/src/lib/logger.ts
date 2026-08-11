// Structured logging, in the same shape gary-api emits. One JSON object per
// line, so one search finds a single user's action in both apps' logs:
//
//   {"timestamp":"2026-08-09T17:50:00.123Z","level":"error","logger":"api",
//    "message":"api.unreachable","app":"gary-web","request_id":"5f2c…",
//    "error":{"type":"TypeError","message":"fetch failed","stack":"…"}}
//
// This runs in the browser, so the lines land in the devtools console rather
// than in a file anyone collects. That is a real loss — nobody is reading
// them after the fact — and the reason the shape is kept anyway is the
// request id: it is the same id gary-api records, so a line copied out of a
// console still finds its other half in gary-api's log.

export const APP = "gary-web";
export const REQUEST_ID_HEADER = "x-request-id";

const LEVELS = { debug: 10, info: 20, warning: 30, error: 40 } as const;
export type Level = keyof typeof LEVELS;

export type Fields = Record<string, unknown>;

// The formatter owns these. A caller passing one gets it renamed with a
// trailing underscore rather than overwriting it — the same rule gary-api
// applies, so a line means the same thing whichever app wrote it.
const RESERVED = new Set(["timestamp", "level", "logger", "message", "app"]);

function floor(): number {
  // Inlined at build time, like every other setting this app has: there is no
  // environment to read in a browser.
  const configured = (process.env.NEXT_PUBLIC_LOG_LEVEL ?? "").toLowerCase();
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

export function write(
  level: Level,
  logger: string,
  message: string,
  fields: Fields = {},
): void {
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
      fields_unserialisable:
        error instanceof Error ? error.message : String(error),
    });
  }

  // warning and error to console.error, the rest to console.log — the split
  // devtools already understands, and the one the specs read.
  const sink = LEVELS[level] >= LEVELS.warning ? console.error : console.log;
  sink(line);
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

/**
 * An id for one call, handed to gary-api so both records of it agree.
 *
 * Minted per call now rather than bound for the length of a request: there is
 * no request here to bind it to. Several calls made for one click therefore
 * carry different ids, which is a real loss of grouping — what survives is
 * the pairing of gary-web's line with gary-api's for the same call.
 */
export function requestId(): string {
  return crypto.randomUUID();
}
