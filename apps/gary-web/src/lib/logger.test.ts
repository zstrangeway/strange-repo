import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getLogger,
  requestId,
  write,
} from "./logger";

let out: string[];
let err: string[];

beforeEach(() => {
  out = [];
  err = [];
  vi.spyOn(console, "log").mockImplementation((chunk) => {
    out.push(String(chunk));
    return true;
  });
  vi.spyOn(console, "error").mockImplementation((chunk) => {
    err.push(String(chunk));
    return true;
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

/** Every line written to stdout, parsed. Parsing is half the assertion. */
function lines(written: string[] = out): Record<string, unknown>[] {
  return written.flatMap((chunk) =>
    chunk
      .split("\n")
      .filter((line) => line.trim())
      .map((line) => JSON.parse(line) as Record<string, unknown>),
  );
}

describe("the shape of a line", () => {
  it("is one JSON object carrying the standard fields", () => {
    write("info", "api", "api.call");

    expect(out).toHaveLength(1);
    // One call per line. The console supplies the newline, so the line itself
    // must not carry one or every entry would be double-spaced.
    expect(out[0].endsWith("\n")).toBe(false);
    expect(lines()[0]).toMatchObject({
      level: "info",
      logger: "api",
      message: "api.call",
      app: "gary-web",
    });
  });

  it("timestamps in UTC ISO-8601 with milliseconds, as gary-api does", () => {
    write("info", "api", "api.call");

    expect(lines()[0].timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
  });

  it("puts call-site fields at the top level", () => {
    write("info", "api", "api.call", { status: 200, path: "/auth/me" });

    expect(lines()[0]).toMatchObject({ status: 200, path: "/auth/me" });
  });

  it("will not let a field overwrite one of the standard ones", () => {
    write("info", "api", "api.call", { level: "urgent", app: "not-gary" });

    expect(lines()[0]).toMatchObject({
      level: "info",
      app: "gary-web",
      level_: "urgent",
      app_: "not-gary",
    });
  });
});

describe("values JSON cannot hold", () => {
  it("unpacks an Error into type, message and stack", () => {
    write("error", "api", "api.unreachable", { error: new TypeError("fetch failed") });

    expect(lines(err)[0].error).toMatchObject({
      type: "TypeError",
      message: "fetch failed",
    });
    expect((lines(err)[0].error as Record<string, string>).stack).toContain("TypeError");
  });

  it("copes with an Error carrying no stack", () => {
    const error = new Error("bare");
    delete error.stack;

    write("error", "api", "api.unreachable", { error });

    expect(lines(err)[0].error).toMatchObject({ type: "Error", message: "bare", stack: "" });
  });

  it("renders a bigint, a function and a symbol rather than dropping the line", () => {
    write("info", "api", "odd", {
      // BigInt(10), not 10n: the literal needs an ES2020 target and this
      // project compiles to ES2017, so the literal fails `next build`.
      big: BigInt(10),
      work: function named() {},
      tag: Symbol("marker"),
    });

    const line = lines()[0];
    expect(line.big).toBe("10");
    expect(line.work).toContain("named");
    expect(line.tag).toBe("Symbol(marker)");
  });

  it("keeps the line when a field is circular", () => {
    const circular: Record<string, unknown> = {};
    circular.self = circular;

    write("info", "api", "api.call", { circular });

    // The line still arrives, still parses, and says why it is short of a
    // field. Throwing from inside a log call would be the worse outcome.
    const line = lines()[0];
    expect(line).toMatchObject({ message: "api.call", app: "gary-web" });
    expect(line.fields_unserialisable).toEqual(expect.any(String));
  });

  it("keeps the line when serialising throws something that is not an Error", () => {
    const nasty = {
      toJSON() {
        throw "just a string";
      },
    };

    write("info", "api", "api.call", { nasty });

    expect(lines()[0]).toMatchObject({
      message: "api.call",
      fields_unserialisable: "just a string",
    });
  });
});

describe("levels", () => {
  it("sends warning and error to stderr, and the rest to stdout", () => {
    vi.stubEnv("NEXT_PUBLIC_LOG_LEVEL", "debug");

    const log = getLogger("api");
    log.debug("a");
    log.info("b");
    log.warning("c");
    log.error("d");

    expect(lines().map((line) => line.message)).toEqual(["a", "b"]);
    expect(lines(err).map((line) => line.message)).toEqual(["c", "d"]);
  });

  it("drops anything below NEXT_PUBLIC_LOG_LEVEL", () => {
    vi.stubEnv("NEXT_PUBLIC_LOG_LEVEL", "ERROR");

    const log = getLogger("api");
    log.info("dropped");
    log.error("kept");

    expect(out).toEqual([]);
    expect(lines(err).map((line) => line.message)).toEqual(["kept"]);
  });

  it("falls back to info when NEXT_PUBLIC_LOG_LEVEL is not a level", () => {
    vi.stubEnv("NEXT_PUBLIC_LOG_LEVEL", "chatty");

    const log = getLogger("api");
    log.debug("dropped");
    log.info("kept");

    expect(lines().map((line) => line.message)).toEqual(["kept"]);
  });

  it("defaults to info when NEXT_PUBLIC_LOG_LEVEL is unset", () => {
    vi.stubEnv("NEXT_PUBLIC_LOG_LEVEL", undefined);

    getLogger("api").debug("dropped");

    expect(out).toEqual([]);
  });
});

describe("requestId", () => {
  it("is a fresh id each time, since there is no request to bind one to", () => {
    expect(requestId()).not.toBe(requestId());
  });

  it("looks like the ids gary-api records", () => {
    expect(requestId()).toMatch(/^[0-9a-f-]{36}$/);
  });
});
