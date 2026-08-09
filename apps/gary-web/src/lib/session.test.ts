import { beforeEach, describe, expect, it, vi } from "vitest";

// Type-only, so it is erased before vi.mock("./api") hoists and cannot
// resurrect the real module this file exists to replace.
import type { SignedIn } from "./api";

const store = {
  get: vi.fn(),
  set: vi.fn(),
  delete: vi.fn(),
};

vi.mock("next/headers", () => ({
  cookies: async () => store,
}));

const callApi = vi.fn();
vi.mock("./api", () => ({
  callApi: (...args: unknown[]) => callApi(...args),
}));

const { SESSION_COOKIE, currentUser, endSession, sessionToken, startSession } =
  await import("./session");

beforeEach(() => {
  vi.clearAllMocks();
  vi.unstubAllEnvs();
});

describe("startSession", () => {
  const signedIn: SignedIn = {
    id: "1",
    email: "ada@example.com",
    display_name: "Ada",
    email_verified: false,
    token: "a-token",
    expires_at: "2030-01-01T00:00:00Z",
  };

  it("sets an httpOnly cookie on gary-web's own origin", async () => {
    await startSession(signedIn);

    expect(store.set).toHaveBeenCalledWith(
      SESSION_COOKIE,
      "a-token",
      expect.objectContaining({
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        expires: new Date("2030-01-01T00:00:00Z"),
      }),
    );
  });

  it("marks the cookie secure in production", async () => {
    vi.stubEnv("NODE_ENV", "production");

    await startSession(signedIn);

    expect(store.set.mock.calls[0][2]).toMatchObject({ secure: true });
  });

  it("leaves it insecure elsewhere, or plain HTTP silently drops it", async () => {
    vi.stubEnv("NODE_ENV", "development");

    await startSession(signedIn);

    expect(store.set.mock.calls[0][2]).toMatchObject({ secure: false });
  });
});

describe("endSession", () => {
  it("deletes the cookie", async () => {
    await endSession();

    expect(store.delete).toHaveBeenCalledWith(SESSION_COOKIE);
  });
});

describe("sessionToken", () => {
  it("returns the token when the cookie is there", async () => {
    store.get.mockReturnValue({ value: "a-token" });

    expect(await sessionToken()).toBe("a-token");
  });

  it("returns null when it is not", async () => {
    store.get.mockReturnValue(undefined);

    expect(await sessionToken()).toBeNull();
  });
});

describe("currentUser", () => {
  it("does not call gary-api without a cookie", async () => {
    store.get.mockReturnValue(undefined);

    expect(await currentUser()).toBeNull();
    expect(callApi).not.toHaveBeenCalled();
  });

  it("returns the user gary-api reports", async () => {
    store.get.mockReturnValue({ value: "a-token" });
    const user = { id: "1", email: "ada@example.com", display_name: "Ada" };
    callApi.mockResolvedValue({ ok: true, data: user });

    expect(await currentUser()).toEqual(user);
    expect(callApi).toHaveBeenCalledWith("/auth/me", { token: "a-token" });
  });

  it("reads a rejected session as signed out rather than an error", async () => {
    store.get.mockReturnValue({ value: "stale" });
    callApi.mockResolvedValue({ ok: false, status: 401, message: "Not signed in" });

    expect(await currentUser()).toBeNull();
  });
});
