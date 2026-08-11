import http from "node:http";
import type { AddressInfo } from "node:net";

import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { callApi } from "./api";

// A real server rather than a stubbed fetch: the bug this file exists to
// prevent was a 202 with an empty body being parsed as JSON, which only a
// real response has.
type Reply = { status: number; body?: string; contentType?: string };

let server: http.Server;
let nextReply: Reply = { status: 200, body: "{}" };
let received: { method: string; url: string; headers: http.IncomingHttpHeaders; body: string };

beforeAll(async () => {
  server = http.createServer((request, response) => {
    const chunks: Buffer[] = [];
    request.on("data", (chunk) => chunks.push(chunk as Buffer));
    request.on("end", () => {
      received = {
        method: request.method ?? "",
        url: request.url ?? "",
        headers: request.headers,
        body: Buffer.concat(chunks).toString(),
      };

      const headers: Record<string, string> = {};
      if (nextReply.body !== undefined) {
        headers["content-type"] = nextReply.contentType ?? "application/json";
      }
      response.writeHead(nextReply.status, headers);
      response.end(nextReply.body);
    });
  });

  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as AddressInfo;
  vi.stubEnv("NEXT_PUBLIC_GARY_API_URL", `http://127.0.0.1:${port}`);
});

afterAll(async () => {
  await new Promise<void>((resolve) => {
    server.close(() => resolve());
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

// callApi logs every call it makes. Captured rather than left to print, so a
// passing run is quiet and the lines are assertable.
const written: { stdout: string[]; stderr: string[] } = { stdout: [], stderr: [] };

beforeEach(() => {
  written.stdout = [];
  written.stderr = [];
  vi.spyOn(console, "log").mockImplementation((chunk) => {
    written.stdout.push(String(chunk));
    return true;
  });
  vi.spyOn(console, "error").mockImplementation((chunk) => {
    written.stderr.push(String(chunk));
    return true;
  });
});

function replyWith(reply: Reply) {
  nextReply = reply;
}

/** Every structured line callApi wrote, parsed. */
function logged(): Record<string, unknown>[] {
  return [...written.stdout, ...written.stderr]
    .flatMap((chunk) => chunk.split("\n"))
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line) as Record<string, unknown>);
}

describe("callApi", () => {
  it("GETs by default and sends no content-type without a body", async () => {
    replyWith({ status: 200, body: JSON.stringify({ ok: 1 }) });

    const result = await callApi<{ ok: number }>("/auth/me");

    expect(result).toEqual({ ok: true, data: { ok: 1 } });
    expect(received.method).toBe("GET");
    expect(received.url).toBe("/auth/me");
    expect(received.headers["content-type"]).toBeUndefined();
    expect(received.headers.authorization).toBeUndefined();
  });

  it("sends the method, body and bearer token it is given", async () => {
    replyWith({ status: 201, body: JSON.stringify({ token: "t" }) });

    await callApi("/auth/sessions", {
      method: "POST",
      body: { email: "ada@example.com" },
      token: "a-token",
    });

    expect(received.method).toBe("POST");
    expect(received.headers["content-type"]).toBe("application/json");
    expect(received.headers.authorization).toBe("Bearer a-token");
    expect(JSON.parse(received.body)).toEqual({ email: "ada@example.com" });
  });

  it("omits the authorization header when the token is null", async () => {
    replyWith({ status: 200, body: "{}" });

    await callApi("/auth/me", { token: null });

    expect(received.headers.authorization).toBeUndefined();
  });

  it("reads an empty success body as no data", async () => {
    // The 202 from /auth/password-reset. Parsing this as JSON used to throw.
    replyWith({ status: 202 });

    const result = await callApi("/auth/password-reset", { method: "POST", body: {} });

    expect(result).toEqual({ ok: true, data: undefined });
  });

  it("reads a 204 as no data", async () => {
    replyWith({ status: 204 });

    expect(await callApi("/auth/me/password", { method: "POST", body: {} })).toEqual({
      ok: true,
      data: undefined,
    });
  });

  it("reports gary-api being unreachable rather than throwing", async () => {
    // Nothing listens on port 1.
    vi.stubEnv("NEXT_PUBLIC_GARY_API_URL", "http://127.0.0.1:1");

    const result = await callApi("/auth/me");

    expect(result).toEqual({
      ok: false,
      status: 0,
      message: "gary is unavailable, try again shortly",
    });
    // One object with the failure inside it, not a stack trace on stderr.
    const line = logged().at(-1)!;
    expect(line).toMatchObject({ message: "api.unreachable", level: "error", path: "/auth/me" });
    expect(line.error).toMatchObject({ type: expect.any(String) });
    expect(line.request_id).toEqual(expect.any(String));

    const { port } = server.address() as AddressInfo;
    vi.stubEnv("NEXT_PUBLIC_GARY_API_URL", `http://127.0.0.1:${port}`);
  });

  it("falls back to 127.0.0.1:8000 when NEXT_PUBLIC_GARY_API_URL is unset", async () => {
    // Undefined, not empty: an empty string is not nullish, so ?? would not
    // reach the default and the branch would go untested.
    vi.stubEnv("NEXT_PUBLIC_GARY_API_URL", undefined);

    // Nothing is listening there in a test run, so the transport failure is
    // the proof it used the default.
    const result = await callApi("/auth/me");
    expect(result).toEqual({
      ok: false,
      status: 0,
      message: "gary is unavailable, try again shortly",
    });

    const { port } = server.address() as AddressInfo;
    vi.stubEnv("NEXT_PUBLIC_GARY_API_URL", `http://127.0.0.1:${port}`);
  });
});

describe("error messages", () => {
  async function messageFor(reply: Reply) {
    replyWith(reply);
    const result = await callApi("/auth/register", { method: "POST", body: {} });
    if (result.ok) {
      throw new Error("expected a failure");
    }
    return result.message;
  }

  it("passes a plain string detail through", async () => {
    expect(
      await messageFor({
        status: 409,
        body: JSON.stringify({ detail: "That email address is already registered" }),
      }),
    ).toBe("That email address is already registered");
  });

  it.each([
    ["password", "Your password needs to be at least 8 characters"],
    ["new_password", "Your password needs to be at least 8 characters"],
    ["email", "That does not look like an email address"],
    ["display_name", "Your display name cannot be blank"],
  ])("turns a 422 on %s into something actionable", async (field, expected) => {
    expect(
      await messageFor({
        status: 422,
        body: JSON.stringify({ detail: [{ loc: ["body", field], msg: "nope" }] }),
      }),
    ).toBe(expected);
  });

  it("falls back to the reported message for a field it does not know", async () => {
    expect(
      await messageFor({
        status: 422,
        body: JSON.stringify({ detail: [{ loc: ["body", "surprise"], msg: "too odd" }] }),
      }),
    ).toBe("too odd");
  });

  it("copes with a 422 whose entry has no message", async () => {
    expect(
      await messageFor({
        status: 422,
        body: JSON.stringify({ detail: [{ loc: ["body", "surprise"] }] }),
      }),
    ).toBe("That does not look right, please check and try again");
  });

  it("copes with a 422 whose entry has no location", async () => {
    expect(
      await messageFor({ status: 422, body: JSON.stringify({ detail: [{ msg: "odd" }] }) }),
    ).toBe("odd");
  });

  it("copes with a 422 whose detail is not a list", async () => {
    expect(
      await messageFor({ status: 422, body: JSON.stringify({ detail: "unexpected" }) }),
    ).toBe("That does not look right, please check and try again");
  });

  it("copes with a 422 whose detail list is empty", async () => {
    expect(await messageFor({ status: 422, body: JSON.stringify({ detail: [] }) })).toBe(
      "That does not look right, please check and try again",
    );
  });

  it("falls back when an error body is not JSON at all", async () => {
    expect(
      await messageFor({ status: 502, body: "<html>bad gateway</html>", contentType: "text/html" }),
    ).toBe("gary is unavailable, try again shortly");
  });

  it("falls back when an error carries a detail that is not a string", async () => {
    expect(await messageFor({ status: 500, body: JSON.stringify({ detail: { a: 1 } }) })).toBe(
      "gary is unavailable, try again shortly",
    );
  });

  it("reports the status it was given", async () => {
    replyWith({ status: 403, body: JSON.stringify({ detail: "no" }) });

    const result = await callApi("/auth/me/password", { method: "POST", body: {} });

    expect(result).toEqual({ ok: false, status: 403, message: "no" });
  });
});
