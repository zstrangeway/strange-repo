import { beforeEach, describe, expect, it } from "vitest";

import { clearFlash, peekFlash, setFlash } from "./flash";

beforeEach(() => {
  clearFlash();
});

describe("flash", () => {
  it("is empty when nothing was set", () => {
    expect(peekFlash()).toEqual({});
  });

  it("hands over what was set", () => {
    setFlash({ confirmation: "Facebook is connected" });
    expect(peekFlash()).toEqual({ confirmation: "Facebook is connected" });
  });

  it("reads the same twice, because reading does not consume it", () => {
    // React may render a component more than once. If the first read emptied
    // it, the second would show nothing and the message would be lost.
    setFlash({ error: "That did not work" });

    expect(peekFlash()).toEqual({ error: "That did not work" });
    expect(peekFlash()).toEqual({ error: "That did not work" });
  });

  it("is gone once cleared", () => {
    setFlash({ error: "That did not work" });
    clearFlash();

    expect(peekFlash()).toEqual({});
  });

  it("keeps only the most recent", () => {
    setFlash({ error: "first" });
    setFlash({ error: "second" });

    expect(peekFlash()).toEqual({ error: "second" });
  });
});
