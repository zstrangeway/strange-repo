import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { callbackUrl, withState } from "./urls";

describe("callbackUrl", () => {
  beforeEach(() => {
    Object.defineProperty(globalThis, "window", {
      value: { location: { origin: "https://gary-web.fly.dev" } },
      configurable: true,
    });
  });

  afterEach(() => {
    Reflect.deleteProperty(globalThis, "window");
  });

  it("is absolute, because a provider has to resolve it", () => {
    expect(callbackUrl("/signed-in")).toBe("https://gary-web.fly.dev/signed-in");
  });

  it("takes the origin from the browser rather than deriving one", () => {
    Object.defineProperty(globalThis, "window", {
      value: { location: { origin: "http://localhost:3999" } },
      configurable: true,
    });

    expect(callbackUrl("/profile/connected")).toBe(
      "http://localhost:3999/profile/connected",
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
    expect(new URL(withState(FROM_API, "facebook")).searchParams.get("state")).toBe(
      "facebook",
    );
  });

  it("replaces the empty state rather than adding a second one", () => {
    // Appending left state= in place and the URL carried it twice, which
    // Facebook refuses to load at all.
    expect(
      new URL(withState(FROM_API, "facebook")).searchParams.getAll("state"),
    ).toEqual(["facebook"]);
  });

  it("leaves the rest of what the provider was given alone", () => {
    const url = new URL(withState(FROM_API, "facebook"));

    expect(url.searchParams.get("redirect_uri")).toBe(
      "https://gary-web.fly.dev/profile/connected",
    );
    expect(url.searchParams.get("scope")).toBe("email public_profile");
  });
});
