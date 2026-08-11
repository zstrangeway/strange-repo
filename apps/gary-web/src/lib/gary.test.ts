import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiResult } from "./api";

const callApi = vi.fn();
vi.mock("./api", () => ({
  callApi: (...args: unknown[]) => callApi(...args),
}));

const store = { token: null as string | null };
vi.mock("./session", () => ({
  storedToken: () => store.token,
  storeToken: (value: string) => {
    store.token = value;
  },
  clearToken: () => {
    store.token = null;
  },
}));

const {
  completeSignIn,
  connectAccount,
  connectedAccounts,
  disconnectAccount,
  me,
  signOut,
  updateDisplayName,
  waysToSignIn,
} = await import("./gary");

function answering<T>(result: ApiResult<T>) {
  callApi.mockResolvedValue(result);
}

const REFUSED = { ok: false, status: 409, message: "Not allowed" } as const;

beforeEach(() => {
  callApi.mockReset();
  store.token = "a-token";
});

describe("waysToSignIn", () => {
  it("asks gary-api where to send people", async () => {
    answering({ ok: true, data: [{ name: "google" }] });
    await waysToSignIn("https://gary-web.fly.dev/signed-in");

    expect(callApi).toHaveBeenCalledWith(
      "/auth/providers?redirect_uri=https%3A%2F%2Fgary-web.fly.dev%2Fsigned-in",
    );
  });

  it("offers nothing rather than failing when gary-api will not say", async () => {
    // The login page has to render either way; an empty list is a message it
    // already knows how to show.
    answering({ ok: false, status: 0, message: "unavailable" });

    expect(await waysToSignIn("/back")).toEqual([]);
  });
});

describe("me", () => {
  it("is nobody when no token is held", async () => {
    store.token = null;

    expect(await me()).toBe(null);
    expect(callApi).not.toHaveBeenCalled();
  });

  it("is whoever gary-api says the token belongs to", async () => {
    answering({ ok: true, data: { id: "1", email: "ada@example.com" } });

    expect(await me()).toEqual({ id: "1", email: "ada@example.com" });
  });

  it("throws away a token gary-api will not honour", async () => {
    // Otherwise every later call fails in a way that reads as a bug rather
    // than as having been signed out.
    answering({ ok: false, status: 401, message: "no" });

    expect(await me()).toBe(null);
    expect(store.token).toBe(null);
  });

  it("keeps the token when gary-api is merely unwell", async () => {
    answering({ ok: false, status: 0, message: "unavailable" });

    expect(await me()).toBe(null);
    expect(store.token).toBe("a-token");
  });
});

describe("completeSignIn", () => {
  it("keeps the token gary-api issues", async () => {
    store.token = null;
    answering({ ok: true, data: { token: "fresh" } });

    expect(await completeSignIn("google", "code", "/back")).toEqual({});
    expect(store.token).toBe("fresh");
  });

  it("reports a refusal and keeps no token", async () => {
    store.token = null;
    answering({ ok: false, status: 401, message: "Sign in did not work" });

    expect(await completeSignIn("google", "code", "/back")).toEqual({
      error: "Sign in did not work",
    });
    expect(store.token).toBe(null);
  });
});

describe("signOut", () => {
  it("ends the session at gary-api as well as forgetting it", async () => {
    answering({ ok: true, data: undefined });
    await signOut();

    expect(callApi).toHaveBeenCalledWith("/auth/sessions/current", {
      method: "DELETE",
      token: "a-token",
    });
    expect(store.token).toBe(null);
  });

  it("forgets it even when gary-api cannot be reached", async () => {
    // Being unable to tell gary-api is not a reason to stay signed in here.
    answering({ ok: false, status: 0, message: "unavailable" });
    await signOut();

    expect(store.token).toBe(null);
  });
});

describe("updateDisplayName", () => {
  it("says so when it worked", async () => {
    answering({ ok: true, data: {} });

    expect(await updateDisplayName("Ada L")).toEqual({
      confirmation: "Your display name has been updated",
    });
  });

  it("passes on what gary-api objected to", async () => {
    answering(REFUSED);

    expect(await updateDisplayName("")).toEqual({ error: "Not allowed" });
  });

  it("refuses without a token rather than asking", async () => {
    store.token = null;

    expect(await updateDisplayName("Ada")).toEqual({
      error: "You are not signed in",
    });
    expect(callApi).not.toHaveBeenCalled();
  });
});

describe("connectedAccounts", () => {
  it("lists what gary-api holds", async () => {
    answering({ ok: true, data: [{ provider: "google" }] });

    expect(await connectedAccounts()).toEqual([{ provider: "google" }]);
  });

  it("is empty without a token", async () => {
    store.token = null;

    expect(await connectedAccounts()).toEqual([]);
  });

  it("is empty when gary-api will not say", async () => {
    answering(REFUSED);

    expect(await connectedAccounts()).toEqual([]);
  });
});

describe("connectAccount", () => {
  it("names the provider it connected", async () => {
    answering({ ok: true, data: { label: "Facebook" } });

    expect(await connectAccount("facebook", "code", "/back")).toEqual({
      confirmation: "Facebook is connected",
    });
  });

  it("passes on a refusal", async () => {
    answering(REFUSED);

    expect(await connectAccount("facebook", "code", "/back")).toEqual({
      error: "Not allowed",
    });
  });

  it("refuses without a token", async () => {
    store.token = null;

    expect(await connectAccount("facebook", "code", "/back")).toEqual({
      error: "You are not signed in",
    });
  });
});

describe("disconnectAccount", () => {
  it("says so when it worked", async () => {
    answering({ ok: true, data: undefined });

    expect(await disconnectAccount("facebook")).toEqual({
      confirmation: "That way of signing in has been removed",
    });
    expect(callApi).toHaveBeenCalledWith("/auth/me/identities/facebook", {
      method: "DELETE",
      token: "a-token",
    });
  });

  it("passes on the reason it was refused", async () => {
    answering(REFUSED);

    expect(await disconnectAccount("google")).toEqual({ error: "Not allowed" });
  });

  it("refuses without a token", async () => {
    store.token = null;

    expect(await disconnectAccount("google")).toEqual({
      error: "You are not signed in",
    });
  });
});
