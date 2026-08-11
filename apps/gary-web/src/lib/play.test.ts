import http from "node:http";
import type { AddressInfo } from "node:net";

import {
  afterAll,
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { parseFrames, takeTurn, type TurnEvent } from "./play";
import { SESSION_KEY } from "./session";

// A real server that writes frames one at a time, rather than a stubbed
// fetch. What this file exists to prove is that events are handled as they
// arrive and that a frame split across chunks is reassembled — and a stub
// that hands over whole frames would agree with an implementation that
// cannot do either.

type Writer = (
  write: (chunk: string | Buffer) => Promise<void>,
) => Promise<void>;

let server: http.Server;
let status = 200;
let body: string | null = null;
let writer: Writer | null = null;
let received: { headers: http.IncomingHttpHeaders; body: string };

beforeAll(async () => {
  server = http.createServer((request, response) => {
    const chunks: Buffer[] = [];
    request.on("data", (chunk) => chunks.push(chunk as Buffer));
    request.on("end", async () => {
      received = {
        headers: request.headers,
        body: Buffer.concat(chunks).toString(),
      };

      if (status !== 200) {
        response.writeHead(status, { "content-type": "application/json" });
        response.end(body ?? "");
        return;
      }

      response.writeHead(200, { "content-type": "text/event-stream" });
      const write = (chunk: string | Buffer) =>
        new Promise<void>((resolve) => {
          response.write(chunk, () => setTimeout(resolve, 1));
        });
      await writer?.(write);
      response.end();
    });
  });

  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as AddressInfo;
  vi.stubEnv("NEXT_PUBLIC_GARY_API_URL", `http://127.0.0.1:${port}`);
});

afterAll(async () => {
  vi.unstubAllEnvs();
  await new Promise<void>((resolve) => server.close(() => resolve()));
});

beforeEach(() => {
  status = 200;
  body = null;
  writer = null;
  const held = new Map<string, string>([[SESSION_KEY, "a-token"]]);
  Object.defineProperty(globalThis, "window", {
    value: {
      localStorage: {
        getItem: (key: string) => held.get(key) ?? null,
        setItem: () => {},
        removeItem: () => {},
      },
    },
    configurable: true,
  });
});

afterEach(() => {
  // @ts-expect-error putting it back the way it was found
  delete globalThis.window;
});

function frame(name: string, payload: unknown) {
  return `event: ${name}\ndata: ${JSON.stringify(payload)}\n\n`;
}

async function collect(message = "hello", signal?: AbortSignal) {
  const seen: TurnEvent[] = [];
  const result = await takeTurn("c-1", message, (e) => seen.push(e), signal);
  return { seen, result };
}

describe("parsing frames", () => {
  it("reads a whole frame", () => {
    const { events, rest } = parseFrames(frame("narration", { text: "hi" }));
    expect(events).toEqual([{ type: "narration", text: "hi" }]);
    expect(rest).toBe("");
  });

  it("keeps a frame that has not finished arriving", () => {
    const whole = frame("narration", { text: "hi" });
    const { events, rest } = parseFrames(whole + "event: narration\ndata: {");
    expect(events).toHaveLength(1);
    expect(rest).toBe("event: narration\ndata: {");
  });

  it("reads several at once", () => {
    const { events } = parseFrames(
      frame("narration", { text: "a" }) + frame("narration", { text: "b" }),
    );
    expect(events).toHaveLength(2);
  });

  it("skips keepalive comments rather than parsing them", () => {
    // A comment line is not JSON, and passing one to JSON.parse would end a
    // turn that was perfectly fine.
    const { events } = parseFrames(
      `: keepalive\n\n` + frame("narration", { text: "hi" }),
    );
    expect(events).toEqual([{ type: "narration", text: "hi" }]);
  });

  it("skips a frame whose data will not parse", () => {
    const { events } = parseFrames("event: narration\ndata: not json\n\n");
    expect(events).toEqual([]);
  });

  it("skips a frame with no event name", () => {
    const { events } = parseFrames("data: {}\n\n");
    expect(events).toEqual([]);
  });

  it("skips a frame with no data", () => {
    const { events } = parseFrames("event: narration\n\n");
    expect(events).toEqual([]);
  });

  it("reads a roll whole", () => {
    const roll = {
      notation: "1d20+3",
      dice: [14],
      modifier: 3,
      total: 17,
      reason: "Perception",
    };
    const { events } = parseFrames(frame("roll", roll));
    expect(events[0]).toEqual({ type: "roll", roll });
  });

  it("reads a world change", () => {
    const { events } = parseFrames(
      frame("world", { kind: "party-moved", place: "the stair" }),
    );
    expect(events[0]).toEqual({
      type: "world",
      change: { kind: "party-moved", place: "the stair" },
    });
  });

  it("reads a turn, a done and a refusal", () => {
    const { events } = parseFrames(
      frame("turn", { turn_id: "t1", role: "gm" }) +
        frame("done", { turn_id: "t1" }) +
        frame("refusal", { detail: "not that" }),
    );
    expect(events.map((e) => e.type)).toEqual(["turn", "done", "refusal"]);
  });

  it("treats an event it does not know as an error rather than dropping it", () => {
    // A frame nobody renders is a turn that appears to stop for no reason.
    const { events } = parseFrames(frame("something-new", { detail: "eh" }));
    expect(events[0]).toEqual({ type: "error", detail: "eh" });
  });

  it("falls back to a readable message when a frame carries none", () => {
    const { events } = parseFrames(frame("error", {}));
    expect(events[0]).toMatchObject({ type: "error" });
    expect((events[0] as { detail: string }).detail).toContain("unavailable");
  });

  it("reads a frame that carries none of the fields it should", () => {
    // Not something gary-api sends. It is here because the alternative to a
    // fallback is undefined reaching a render, and a turn that renders the
    // word "undefined" is worse than one that renders nothing.
    const { events } = parseFrames(
      frame("turn", {}) + frame("narration", {}) + frame("done", {}) +
        frame("refusal", {}),
    );

    expect(events[0]).toEqual({ type: "turn", turn_id: "", role: "" });
    expect(events[1]).toEqual({ type: "narration", text: "" });
    expect(events[2]).toEqual({ type: "done", turn_id: "" });
    expect((events[3] as { detail: string }).detail).toContain("unavailable");
  });
});

describe("taking a turn", () => {
  it("carries the token and a request id", async () => {
    writer = async (write) => {
      await write(frame("done", { turn_id: "t1" }));
    };
    await collect();
    expect(received.headers.authorization).toBe("Bearer a-token");
    expect(received.headers["x-request-id"]).toBeTruthy();
    expect(JSON.parse(received.body)).toEqual({ message: "hello" });
  });

  it("hands over an event before the turn is over", async () => {
    // Causal rather than timed: the server holds the stream open until the
    // first event has been handed over, and only the callback can release it.
    // A client that buffered the whole body would never call back, and this
    // would hang rather than quietly pass.
    let release = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });

    writer = async (write) => {
      await write(frame("narration", { text: "The door groans." }));
      await held;
      await write(frame("done", { turn_id: "t1" }));
    };

    const seen: TurnEvent[] = [];
    await takeTurn("c-1", "hello", (event) => {
      seen.push(event);
      if (seen.length === 1) release();
    });

    expect(seen.map((event) => event.type)).toEqual(["narration", "done"]);
  });

  it("reassembles a frame split across chunks", async () => {
    const whole = frame("narration", { text: "halved" });
    writer = async (write) => {
      await write(whole.slice(0, 12));
      await write(whole.slice(12));
      await write(frame("done", { turn_id: "t1" }));
    };
    const { seen } = await collect();
    expect(seen[0]).toEqual({ type: "narration", text: "halved" });
  });

  it("reassembles a character split across chunks", async () => {
    // Decoding a multi-byte character in halves puts a replacement character
    // in the middle of a word.
    const whole = Buffer.from(frame("narration", { text: "a café" }), "utf8");
    const cut = whole.length - 6;
    writer = async (write) => {
      await write(whole.subarray(0, cut));
      await write(whole.subarray(cut));
    };
    const { seen } = await collect();
    expect((seen[0] as { text: string }).text).toContain("café");
  });

  it("reports a refusal from before the stream opened", async () => {
    status = 409;
    body = JSON.stringify({ detail: "Nobody to play", code: "no_party" });
    const { seen, result } = await collect();
    expect(seen).toEqual([]);
    expect(result).toEqual({
      ok: false,
      message: "Nobody to play",
      code: "no_party",
    });
  });

  it("reports a refusal that carried no readable body", async () => {
    status = 500;
    body = "<html>gateway</html>";
    const { result } = await collect();
    expect(result.ok).toBe(false);
    expect(result.message).toContain("unavailable");
    expect(result.code).toBeUndefined();
  });

  it("reports a success with nothing to read", async () => {
    // Not something gary-api does. A proxy that collected the whole response
    // and then handed back nothing looks exactly like this, and it is worth
    // reading as gary being unavailable rather than as a turn that silently
    // produced no narration.
    status = 204;
    body = "";
    const { seen, result } = await collect();
    expect(seen).toEqual([]);
    expect(result.ok).toBe(false);
    expect(result.message).toContain("unavailable");
  });

  it("reports a refusal whose body is literally null", async () => {
    // JSON.parse("null") succeeds and gives null, which is not an object and
    // would throw on the property read that follows.
    status = 409;
    body = "null";
    const { result } = await collect();
    expect(result.ok).toBe(false);
    expect(result.message).toContain("unavailable");
  });

  it("falls back to 127.0.0.1:8000 when NEXT_PUBLIC_GARY_API_URL is unset", async () => {
    // Undefined, not empty: an empty string is not nullish, so ?? would not
    // reach the default and the branch would go untested.
    vi.stubEnv("NEXT_PUBLIC_GARY_API_URL", undefined);

    // Nothing is listening there in a test run, so the transport failure is
    // the proof it used the default.
    const { result } = await collect();
    expect(result.ok).toBe(false);
    expect(result.message).toContain("unavailable");

    const { port } = server.address() as AddressInfo;
    vi.stubEnv("NEXT_PUBLIC_GARY_API_URL", `http://127.0.0.1:${port}`);
  });

  it("reports gary-api being unreachable", async () => {
    vi.stubEnv("NEXT_PUBLIC_GARY_API_URL", "http://127.0.0.1:1");
    const { result } = await collect();
    expect(result.ok).toBe(false);
    expect(result.message).toContain("unavailable");
    const { port } = server.address() as AddressInfo;
    vi.stubEnv("NEXT_PUBLIC_GARY_API_URL", `http://127.0.0.1:${port}`);
  });

  it("works without a token, so the refusal comes from gary-api", async () => {
    // @ts-expect-error no window at all, as during a build
    delete globalThis.window;
    writer = async (write) => {
      await write(frame("done", { turn_id: "t1" }));
    };
    await collect();
    expect(received.headers.authorization).toBeUndefined();
  });

  it("says nothing when the reader is aborted", async () => {
    const controller = new AbortController();
    writer = async (write) => {
      await write(frame("narration", { text: "starting" }));
      controller.abort();
      await new Promise((resolve) => setTimeout(resolve, 30));
      await write(frame("narration", { text: "never seen" }));
    };

    const seen: TurnEvent[] = [];
    await takeTurn("c-1", "hello", (e) => seen.push(e), controller.signal);
    expect(seen.every((event) => event.type !== "error")).toBe(true);
  });

  it("reports a stream that breaks for a reason other than abort", async () => {
    writer = async (write) => {
      await write(frame("narration", { text: "half a " }));
      // Tear the socket out from under it.
      server.closeAllConnections?.();
      await new Promise((resolve) => setTimeout(resolve, 20));
    };
    const { seen } = await collect();
    expect(seen.some((event) => event.type === "error")).toBe(true);
  });
});
