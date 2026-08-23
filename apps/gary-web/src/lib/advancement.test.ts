import { describe, expect, it } from "vitest";

import {
  asAward,
  asLevel,
  progress,
  readAward,
  readLevel,
} from "./advancement";

describe("progress", () => {
  it("says how far along somebody is", () => {
    expect(progress({ experience: 150, next_level: 300 })).toEqual({
      have: 150,
      needed: 300,
      fraction: 0.5,
    });
  });

  it("has nothing to say when there is no next level", () => {
    // The top of a system that prices levels, and every level of one that
    // does not, both arrive as null and both mean the same thing here.
    expect(progress({ experience: 355000, next_level: null })).toBeNull();
  });

  it("has nothing to say when the next level costs nothing", () => {
    expect(progress({ experience: 0, next_level: 0 })).toBeNull();
  });

  it("does not run past the end", () => {
    // Experience keeps accruing past a threshold until the level is written,
    // and a bar past full reads as a bug rather than as being ahead.
    expect(progress({ experience: 400, next_level: 300 })?.fraction).toBe(1);
  });
});

describe("telling the two events apart", () => {
  it("reads an award", () => {
    expect(
      asAward({
        kind: "experience-gained",
        character: "Bramble",
        amount: 300,
        reason: "the mud creature",
      }),
    ).toEqual({ character: "Bramble", amount: 300, reason: "the mud creature" });
  });

  it("is not fooled by another change", () => {
    expect(asAward({ kind: "party-moved", place: "the stair" })).toBeNull();
    expect(asLevel({ kind: "party-moved", place: "the stair" })).toBeNull();
  });

  it("reads a level", () => {
    expect(
      asLevel({
        kind: "level-gained",
        character: "Bramble",
        level: 2,
        hit_points: 5,
      }),
    ).toEqual({ character: "Bramble", level: 2, hit_points: 5 });
  });

  it("survives a frame with nothing in it", () => {
    // Frames come off the network. A missing field should read as empty
    // rather than as NaN on somebody's screen.
    expect(asAward({ kind: "experience-gained" })).toEqual({
      character: "",
      amount: 0,
      reason: "",
    });
    expect(asLevel({ kind: "level-gained" })).toEqual({
      character: "",
      level: 0,
      hit_points: 0,
    });
  });
});

describe("what they read as", () => {
  it("says what an award was for", () => {
    expect(
      readAward({ character: "Bramble", amount: 300, reason: "the belfry" }),
    ).toBe("Bramble gained 300 experience for the belfry");
  });

  it("leaves the reason off when there is none", () => {
    expect(readAward({ character: "Bramble", amount: 300, reason: "" })).toBe(
      "Bramble gained 300 experience",
    );
  });

  it("says what a level brought", () => {
    expect(readLevel({ character: "Bramble", level: 2, hit_points: 5 })).toBe(
      "Bramble reached level 2, and 5 hit points with it",
    );
  });
});
