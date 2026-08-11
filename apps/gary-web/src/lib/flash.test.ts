import { describe, expect, it } from "vitest";

import { FLASH_COOKIE, flashCookie, readFlash } from "./flash";

describe("flashCookie", () => {
  it("carries the message across a redirect", () => {
    const raw = flashCookie({ error: "That is your only way to sign in" });
    const value = raw.split(";")[0].slice(`${FLASH_COOKIE}=`.length);

    expect(readFlash(decodeURIComponent(value))).toEqual({
      error: "That is your only way to sign in",
    });
  });

  it("is scoped to the site and expires on its own", () => {
    // A backstop for the browser that never runs the clearing effect: a
    // message that outlived its page is worse than one that vanished.
    const raw = flashCookie({ confirmation: "Facebook is connected" });

    expect(raw).toContain("Path=/");
    expect(raw).toContain("SameSite=Lax");
    expect(raw).toMatch(/Max-Age=\d+/);
  });

  it("escapes what it is given rather than pasting it in", () => {
    const raw = flashCookie({ error: "semicolons; commas, and spaces" });

    expect(raw.split(";")[0]).not.toContain(" ");
    expect(raw.split(";")[0]).not.toContain(",");
  });
});

describe("readFlash", () => {
  it("is empty when nothing was set", () => {
    expect(readFlash(undefined)).toEqual({});
  });

  it("is empty rather than throwing on something it did not write", () => {
    // The cookie is readable by script, so it can be anything at all.
    expect(readFlash("not json")).toEqual({});
  });

  it("ignores fields it does not know", () => {
    expect(readFlash('{"error":"nope","danger":"<script>"}')).toEqual({
      error: "nope",
    });
  });

  it("reads a confirmation as readily as an error", () => {
    expect(readFlash('{"confirmation":"Facebook is connected"}')).toEqual({
      confirmation: "Facebook is connected",
    });
  });

  it("is empty for valid JSON that is not an object", () => {
    expect(readFlash("5")).toEqual({});
  });

  it("is empty for a literal null, which claims to be an object", () => {
    expect(readFlash("null")).toEqual({});
  });

  it("keeps only strings", () => {
    expect(readFlash('{"error":{"toString":"clever"}}')).toEqual({});
  });
});
