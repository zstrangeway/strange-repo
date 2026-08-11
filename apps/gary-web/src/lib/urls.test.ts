import { beforeEach, describe, expect, it, vi } from "vitest";

const received = { get: vi.fn() };

vi.mock("next/headers", () => ({
  headers: async () => received,
}));

const { absoluteUrl, withState } = await import("./urls");

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

describe("withState", () => {
  // gary-api serves the authorization URL with an empty state for callers
  // that have not chosen one, so the empty parameter is what arrives here.
  const FROM_API =
    "https://www.facebook.com/v5.0/dialog/oauth?response_type=code" +
    "&client_id=123&redirect_uri=https%3A%2F%2Fgary-web.fly.dev%2Fprofile%2Fconnected" +
    "&state=&scope=email+public_profile";

  it("carries the provider so the callback knows who came back", () => {
    const url = new URL(withState(FROM_API, "facebook"));

    expect(url.searchParams.get("state")).toBe("facebook");
  });

  it("replaces the empty state rather than adding a second one", () => {
    // Appending left state= in place and the URL carried it twice, which
    // Facebook refuses to load at all.
    const url = new URL(withState(FROM_API, "facebook"));

    expect(url.searchParams.getAll("state")).toEqual(["facebook"]);
  });

  it("leaves the rest of what the provider was given alone", () => {
    const url = new URL(withState(FROM_API, "facebook"));

    expect(url.searchParams.get("redirect_uri")).toBe(
      "https://gary-web.fly.dev/profile/connected",
    );
    expect(url.searchParams.get("scope")).toBe("email public_profile");
  });
});
