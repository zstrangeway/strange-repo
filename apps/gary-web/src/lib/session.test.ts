import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { SESSION_KEY, clearToken, storedToken, storeToken } from "./session";

/** A localStorage that lives in this process, since these run under node. */
function fakeStorage() {
  const held = new Map<string, string>();
  return {
    getItem: (key: string) => held.get(key) ?? null,
    setItem: (key: string, value: string) => void held.set(key, value),
    removeItem: (key: string) => void held.delete(key),
  };
}

describe("in a browser", () => {
  beforeEach(() => {
    Object.defineProperty(globalThis, "window", {
      value: { localStorage: fakeStorage() },
      configurable: true,
    });
  });

  afterEach(() => {
    Reflect.deleteProperty(globalThis, "window");
  });

  it("has no token until one is stored", () => {
    expect(storedToken()).toBe(null);
  });

  it("keeps a token across reads", () => {
    storeToken("a-token");
    expect(storedToken()).toBe("a-token");
  });

  it("forgets it when cleared", () => {
    storeToken("a-token");
    clearToken();
    expect(storedToken()).toBe(null);
  });

  it("stores it under a name that will not collide", () => {
    storeToken("a-token");
    expect(window.localStorage.getItem(SESSION_KEY)).toBe("a-token");
  });
});

describe("outside a browser", () => {
  // This module is imported while the app is being built, where there is no
  // window at all. Touching localStorage there would throw during the build.
  it("reads nothing rather than throwing", () => {
    expect(storedToken()).toBe(null);
  });

  it("stores nothing rather than throwing", () => {
    expect(() => storeToken("a-token")).not.toThrow();
    expect(() => clearToken()).not.toThrow();
  });
});
