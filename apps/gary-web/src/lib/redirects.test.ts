import { describe, expect, it } from "vitest";

import { seeOther } from "./redirects";

describe("seeOther", () => {
  it("names no host, so the browser supplies the right one", () => {
    const location = seeOther("/profile").headers.get("location");

    expect(location).toBe("/profile");
    expect(location).not.toContain("://");
  });

  it("carries query parameters when there are any", () => {
    const location =
      seeOther("/profile", { connected: "Google" }).headers.get("location") ??
      "";

    expect(location.startsWith("/profile?")).toBe(true);
    expect(new URLSearchParams(location.split("?")[1]).get("connected")).toBe(
      "Google",
    );
  });

  it("escapes what it is given rather than pasting it in", () => {
    const location =
      seeOther("/login", { error: "Sign in with Google did not work" }).headers.get(
        "location",
      ) ?? "";

    expect(location).not.toContain(" ");
    expect(new URLSearchParams(location.split("?")[1]).get("error")).toBe(
      "Sign in with Google did not work",
    );
  });

  it("redirects a GET to a GET", () => {
    expect(seeOther("/").status).toBe(303);
  });
});
