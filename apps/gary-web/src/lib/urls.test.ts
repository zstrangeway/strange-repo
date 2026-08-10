import { beforeEach, describe, expect, it, vi } from "vitest";

const received = { get: vi.fn() };

vi.mock("next/headers", () => ({
  headers: async () => received,
}));

const { absoluteUrl } = await import("./urls");

beforeEach(() => {
  vi.clearAllMocks();
});

function serving(headers: Record<string, string | null>) {
  received.get.mockImplementation((name: string) => headers[name] ?? null);
}

describe("absoluteUrl", () => {
  it("builds from the host the request arrived on", async () => {
    serving({ host: "gary-web.fly.dev", "x-forwarded-proto": "https" });

    expect(await absoluteUrl("/signed-in")).toBe(
      "https://gary-web.fly.dev/signed-in",
    );
  });

  it("is plain http where nothing terminated TLS", async () => {
    serving({ host: "localhost:3999" });

    expect(await absoluteUrl("/signed-in")).toBe(
      "http://localhost:3999/signed-in",
    );
  });

  it("falls back to a local host rather than building a bare path", async () => {
    // A redirect_uri that is not absolute is rejected by every provider, so
    // guessing beats returning something that cannot possibly work.
    serving({});

    expect(await absoluteUrl("/signed-in")).toBe(
      "http://localhost:3000/signed-in",
    );
  });
});
