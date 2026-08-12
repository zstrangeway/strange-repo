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
  addCharacter,
  beginScene,
  campaign,
  catalogue,
  completeSignIn,
  connectAccount,
  connectedAccounts,
  disconnectAccount,
  me,
  myCampaigns,
  partyOf,
  runnableModels,
  scenesOf,
  signOut,
  startCampaign,
  systemNamed,
  rollScores,
  takeOver,
  transcript,
  updateDisplayName,
  changeModel,
  waysToSignIn,
  worldOf,
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

// ---------------------------------------------------------------- the game
//
// The pattern below is the same one the account half uses: gary-api being
// unwell is not an exception here, it is an empty list or a null, because
// every one of these renders into a page that has to render either way.

describe("catalogue", () => {
  it("asks for the systems without a token", async () => {
    // A menu, not somebody's data — and part of deciding whether to sign up
    // at all, so asking for a session would be asking too early.
    answering({ ok: true, data: [{ slug: "dnd-5e" }] });

    expect(await catalogue()).toEqual([{ slug: "dnd-5e" }]);
    expect(callApi).toHaveBeenCalledWith("/catalogue");
  });

  it("offers nothing rather than failing", async () => {
    answering(REFUSED);

    expect(await catalogue()).toEqual([]);
  });
});

describe("systemNamed", () => {
  it("asks for the one system", async () => {
    answering({ ok: true, data: { slug: "dnd-5e", classes: ["rogue"] } });

    expect(await systemNamed("dnd-5e")).toEqual({
      slug: "dnd-5e",
      classes: ["rogue"],
    });
    expect(callApi).toHaveBeenCalledWith("/catalogue/dnd-5e");
  });

  it("is nobody's system when gary-api does not know it", async () => {
    answering({ ok: false, status: 404, message: "No such system" });

    expect(await systemNamed("gurps")).toBe(null);
  });
});

describe("runnableModels", () => {
  it("asks for the models that can hold gary's contract", async () => {
    answering({ ok: true, data: [{ id: "anthropic/claude-opus-5" }] });

    expect(await runnableModels()).toEqual([{ id: "anthropic/claude-opus-5" }]);
    expect(callApi).toHaveBeenCalledWith("/models");
  });

  it("offers nothing rather than failing", async () => {
    answering(REFUSED);

    expect(await runnableModels()).toEqual([]);
  });
});

describe("myCampaigns", () => {
  it("carries the token", async () => {
    answering({ ok: true, data: [{ id: "c1" }] });

    expect(await myCampaigns()).toEqual([{ id: "c1" }]);
    expect(callApi).toHaveBeenCalledWith("/campaigns", { token: "a-token" });
  });

  it("is empty when gary-api will not say", async () => {
    answering(REFUSED);

    expect(await myCampaigns()).toEqual([]);
  });
});

describe("campaign", () => {
  it("asks for the one campaign", async () => {
    answering({ ok: true, data: { id: "c1", name: "A Light in the Deep" } });

    expect(await campaign("c1")).toEqual({
      id: "c1",
      name: "A Light in the Deep",
    });
    expect(callApi).toHaveBeenCalledWith("/campaigns/c1", { token: "a-token" });
  });

  it("is nothing when it is not yours", async () => {
    // 404 rather than 403, and the page has a not-found to render.
    answering({ ok: false, status: 404, message: "No such campaign" });

    expect(await campaign("c1")).toBe(null);
  });
});

describe("startCampaign", () => {
  const fields = {
    name: "A Light in the Deep",
    system: "dnd-5e",
    module: "the-drowned-belfry",
    model: null,
  };

  it("hands back the campaign it started", async () => {
    answering({ ok: true, data: { id: "c1" } });

    expect(await startCampaign(fields)).toEqual({ campaign: { id: "c1" } });
    expect(callApi).toHaveBeenCalledWith("/campaigns", {
      method: "POST",
      body: fields,
      token: "a-token",
    });
  });

  it("passes on why it was refused", async () => {
    answering(REFUSED);

    expect(await startCampaign(fields)).toEqual({ error: "Not allowed" });
  });
});

describe("changeModel", () => {
  it("moves the campaign to another model", async () => {
    answering({ ok: true, data: { id: "c1", model: "x/cheap" } });

    expect(await changeModel("c1", "x/cheap")).toEqual({
      campaign: { id: "c1", model: "x/cheap" },
    });
    expect(callApi).toHaveBeenCalledWith("/campaigns/c1", {
      method: "PATCH",
      body: { model: "x/cheap" },
      token: "a-token",
    });
  });

  it("hands it back to the deployment's default", async () => {
    answering({ ok: true, data: { id: "c1", model_chosen: false } });
    await changeModel("c1", null);

    expect(callApi).toHaveBeenCalledWith("/campaigns/c1", {
      method: "PATCH",
      body: { model: null },
      token: "a-token",
    });
  });

  it("passes on why it was refused", async () => {
    answering(REFUSED);

    expect(await changeModel("c1", "x/nonsense")).toEqual({ error: "Not allowed" });
  });
});

describe("addCharacter", () => {
  it("hands back the character it made", async () => {
    answering({ ok: true, data: { id: "ch1", name: "Bramble" } });

    expect(
      await addCharacter("c1", {
        name: "Bramble",
        character_class: "rogue",
        mine: true,
      }),
    ).toEqual({ character: { id: "ch1", name: "Bramble" } });
    expect(callApi).toHaveBeenCalledWith("/campaigns/c1/characters", {
      method: "POST",
      body: { name: "Bramble", character_class: "rogue", mine: true },
      token: "a-token",
    });
  });

  it("passes on why it was refused", async () => {
    answering(REFUSED);

    expect(
      await addCharacter("c1", {
        name: "",
        character_class: "rogue",
        mine: false,
      }),
    ).toEqual({ error: "Not allowed" });
  });
});

describe("worldOf", () => {
  it("asks for the world as it currently stands", async () => {
    answering({ ok: true, data: { place: "the belfry stair", party: [] } });

    expect(await worldOf("c1")).toEqual({
      place: "the belfry stair",
      party: [],
    });
    expect(callApi).toHaveBeenCalledWith("/campaigns/c1/world", {
      token: "a-token",
    });
  });

  it("is nothing when gary-api will not say", async () => {
    answering(REFUSED);

    expect(await worldOf("c1")).toBe(null);
  });
});

describe("transcript", () => {
  it("asks for everything said so far", async () => {
    answering({ ok: true, data: [{ id: "t1", role: "player" }] });

    expect(await transcript("c1")).toEqual([{ id: "t1", role: "player" }]);
    expect(callApi).toHaveBeenCalledWith("/campaigns/c1/turns", {
      token: "a-token",
    });
  });

  it("is empty when gary-api will not say", async () => {
    // The stream carries what happens next, so an empty transcript is a
    // playable table rather than a broken one.
    answering(REFUSED);

    expect(await transcript("c1")).toEqual([]);
  });
});

describe("scenesOf", () => {
  it("asks for every scene", async () => {
    answering({ ok: true, data: [{ id: "s1", number: 1, open: true }] });

    expect(await scenesOf("c1")).toEqual([{ id: "s1", number: 1, open: true }]);
    expect(callApi).toHaveBeenCalledWith("/campaigns/c1/scenes", {
      token: "a-token",
    });
  });

  it("is empty when gary-api will not say", async () => {
    // The table still renders; it just draws no seams.
    answering(REFUSED);

    expect(await scenesOf("c1")).toEqual([]);
  });
});

describe("beginScene", () => {
  it("hands back the scene it opened", async () => {
    answering({ ok: true, data: { id: "s2", number: 2, open: true } });

    expect(await beginScene("c1", "The flooded nave")).toEqual({
      scene: { id: "s2", number: 2, open: true },
    });
    expect(callApi).toHaveBeenCalledWith("/campaigns/c1/scenes", {
      method: "POST",
      body: { title: "The flooded nave" },
      token: "a-token",
    });
  });

  it("passes on why it was refused", async () => {
    answering(REFUSED);

    expect(await beginScene("c1", "")).toEqual({ error: "Not allowed" });
  });
});

describe("partyOf", () => {
  it("asks who is at the table and who plays them", async () => {
    answering({ ok: true, data: [{ id: "ch1", played_by: "player" }] });

    expect(await partyOf("c1")).toEqual([{ id: "ch1", played_by: "player" }]);
    expect(callApi).toHaveBeenCalledWith("/campaigns/c1/characters", {
      token: "a-token",
    });
  });

  it("is empty when gary-api will not say", async () => {
    answering(REFUSED);

    expect(await partyOf("c1")).toEqual([]);
  });
});

describe("takeOver", () => {
  it("hands back the whole party, because two of them changed", async () => {
    answering({
      ok: true,
      data: [
        { id: "ch1", played_by: "gary" },
        { id: "ch2", played_by: "player" },
      ],
    });

    const result = await takeOver("c1", "ch2");
    expect(result.party).toHaveLength(2);
    expect(callApi).toHaveBeenCalledWith("/campaigns/c1/characters/ch2/player", {
      method: "POST",
      token: "a-token",
    });
  });

  it("passes on why it was refused", async () => {
    answering(REFUSED);

    expect(await takeOver("c1", "nobody")).toEqual({ error: "Not allowed" });
  });
});


describe("rollScores", () => {
  it("asks gary-api for them rather than rolling any here", async () => {
    // The same argument that keeps dice away from the model: a number this
    // app produced is a number somebody typed.
    answering({
      ok: true,
      data: {
        method: "roll-4d6-drop-lowest",
        scores: [{ score: 15, dice: [6, 5, 4, 1], dropped: 1 }],
        assigned: null,
      },
    });

    const result = await rollScores("c1", "roll-4d6-drop-lowest");
    expect(result.rolled?.scores[0].score).toBe(15);
    expect(callApi).toHaveBeenCalledWith("/campaigns/c1/scores", {
      method: "POST",
      body: { method: "roll-4d6-drop-lowest" },
      token: "a-token",
    });
  });

  it("passes on a method this system does not offer", async () => {
    answering(REFUSED);
    const result = await rollScores("c1", "roll-3d6-in-order");
    expect(result.rolled).toBeUndefined();
    expect(result.error).toBe(REFUSED.message);
  });
});
