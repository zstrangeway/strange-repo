import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

// The public host, as Fly's proxy passes it on.
const PUBLIC_HOST = "gary-web.fly.dev";

// What the server sees itself as. Next builds request.url from the address
// the server is bound to, which in a container is 0.0.0.0 — and a redirect
// built from it sends the browser somewhere it will refuse to go.
const INTERNAL_ORIGIN = "http://0.0.0.0:8080";

vi.mock("next/headers", () => ({
  headers: async () =>
    new Headers({ host: PUBLIC_HOST, "x-forwarded-proto": "https" }),
}));

const completeSignIn = vi.fn();
vi.mock("../../actions", () => ({
  completeSignIn: (...args: unknown[]) => completeSignIn(...args),
}));

const { GET } = await import("./route");

function arriveBack(query: string) {
  return GET(
    new NextRequest(`${INTERNAL_ORIGIN}/signed-in${query}`, {
      headers: { host: PUBLIC_HOST },
    }),
  );
}

describe("coming back from a provider", () => {
  beforeEach(() => {
    completeSignIn.mockReset();
    completeSignIn.mockResolvedValue({});
  });

  it("sends people somewhere their browser can follow", async () => {
    // The regression: this used to be an absolute URL onto 0.0.0.0, which
    // Safari refuses outright — after signing the person in, so they were
    // logged in and looking at an error at the same time.
    const response = await arriveBack("?code=abc&state=google");
    const location = response.headers.get("location") ?? "";

    expect(location).not.toContain("0.0.0.0");
    expect(location).toBe("/");
  });

  it("asks the provider to return to the public address", async () => {
    await arriveBack("?code=abc&state=google");

    expect(completeSignIn).toHaveBeenCalledWith(
      "google",
      "abc",
      `https://${PUBLIC_HOST}/signed-in`,
    );
  });

  it("returns someone who changed their mind to the sign-in page", async () => {
    const response = await arriveBack("?error=access_denied");

    expect(response.headers.get("location")).toBe("/login");
    expect(completeSignIn).not.toHaveBeenCalled();
  });

  it("carries a refusal back to the sign-in page", async () => {
    completeSignIn.mockResolvedValue({ error: "Google did not work" });
    const response = await arriveBack("?code=abc&state=google");
    const location = response.headers.get("location") ?? "";

    expect(location).not.toContain("0.0.0.0");
    expect(location.startsWith("/login?")).toBe(true);
    expect(new URLSearchParams(location.split("?")[1]).get("error")).toBe(
      "Google did not work",
    );
  });
});
