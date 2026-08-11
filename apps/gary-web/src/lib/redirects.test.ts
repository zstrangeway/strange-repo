import { describe, expect, it } from "vitest";

import { FLASH_COOKIE } from "./flash";
import { seeOther } from "./redirects";

describe("seeOther", () => {
  it("names no host, so the browser supplies the right one", () => {
    const location = seeOther("/profile").headers.get("location");

    expect(location).toBe("/profile");
    expect(location).not.toContain("://");
  });

  it("redirects a GET to a GET", () => {
    expect(seeOther("/").status).toBe(303);
  });

  it("says nothing when there is nothing to say", () => {
    expect(seeOther("/profile").headers.get("set-cookie")).toBe(null);
  });

  it("carries a message in a cookie rather than the address bar", () => {
    const response = seeOther("/profile", { confirmation: "Facebook is connected" });

    expect(response.headers.get("location")).toBe("/profile");
    expect(response.headers.get("set-cookie")).toContain(FLASH_COOKIE);
  });

  it("leaves the path clean whatever the message is", () => {
    const response = seeOther("/login", {
      error: "Sign in with Google did not work",
    });

    expect(response.headers.get("location")).toBe("/login");
  });
});
