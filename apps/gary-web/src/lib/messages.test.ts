import { describe, expect, it } from "vitest";

import { messageFor } from "./messages";

describe("messageFor", () => {
  it("uses gary-web's own words for a refusal it knows", () => {
    expect(messageFor("last_identity", "That is your only way to sign in")).toBe(
      "That is your only way to sign in, so it cannot be removed.",
    );
  });

  it("falls through to what gary-api said for one it does not", () => {
    // A refusal added to gary-api shows up here before anyone writes copy for
    // it, which beats a shrug.
    expect(messageFor("teapot", "gary is a teapot")).toBe("gary is a teapot");
  });

  it("falls through when there is no code at all", () => {
    expect(messageFor(undefined, "gary is unavailable")).toBe(
      "gary is unavailable",
    );
  });

  it("falls through rather than showing an empty string", () => {
    // Guards the lookup being truthy-checked rather than key-checked: an
    // entry set to "" would otherwise render as no message at all.
    expect(messageFor("provider_refused", "fallback")).not.toBe("");
  });
});
