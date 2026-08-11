import { describe, expect, it } from "vitest";

import type { Roll } from "./api";
import { abilityAside, workedOut } from "./rolls";

function aRoll(over: Partial<Roll> = {}): Roll {
  return {
    notation: "1d20",
    dice: [9],
    modifier: 0,
    total: 9,
    reason: "avoid collapse",
    ...over,
  };
}

function aCheck(over: Partial<Roll> = {}): Roll {
  return aRoll({ dc: 12, degree: "success", ...over });
}

describe("workedOut", () => {
  it("stays quiet about a bare roll whose total is its only die", () => {
    // "rolled 5" beside "1d6 → 5" is the same number twice, and a busy turn
    // carries seven of them.
    expect(workedOut(aRoll())).toBeNull();
  });

  it("shows the faces of a check even when nothing was added", () => {
    // The one that was wrong on screen: every score was a ten, so no check
    // ever had a modifier, so no check ever showed its working. "12 vs 12"
    // asks you to trust that the 12 was the die.
    expect(workedOut(aCheck({ dice: [12], total: 12 }))).toBe("rolled 12");
  });

  it("shows the arithmetic when something was added", () => {
    expect(
      workedOut(aRoll({ notation: "1d20+3", dice: [9], modifier: 3, total: 12 })),
    ).toBe("rolled 9 + 3 = 12");
  });

  it("names the ability beside the modifier it produced", () => {
    expect(
      workedOut(
        aCheck({ notation: "1d20+3", dice: [9], modifier: 3, total: 12, ability: "dex" }),
      ),
    ).toBe("rolled 9 + 3 dex = 12");
  });

  it("shows a penalty as a subtraction rather than a negative", () => {
    // "9 + -1" is arithmetic nobody writes down.
    expect(
      workedOut(
        aCheck({ notation: "1d20-1", dice: [9], modifier: -1, total: 8, ability: "dex" }),
      ),
    ).toBe("rolled 9 − 1 dex = 8");
  });

  it("shows every die when there was more than one", () => {
    expect(
      workedOut(aRoll({ notation: "2d6", dice: [3, 4], modifier: 0, total: 7 })),
    ).toBe("rolled 3 + 4 = 7");
  });

  it("shows dice and a modifier together", () => {
    expect(
      workedOut(aRoll({ notation: "2d6+2", dice: [3, 4], modifier: 2, total: 9 })),
    ).toBe("rolled 3 + 4 + 2 = 9");
  });

  it("says nothing about a roll with no dice at all", () => {
    // Not something gary-api sends, but a card that threw on one would take
    // the whole transcript down with it.
    expect(workedOut(aRoll({ dice: [], total: 0 }))).toBeNull();
  });
});

describe("abilityAside", () => {
  it("names the ability of a check that no modifier came out of", () => {
    // A dexterity check that a sheet of straight tens made worth nothing is
    // still a dexterity check.
    expect(abilityAside(aCheck({ ability: "dex" }))).toBe("dex");
  });

  it("says nothing when the working already named it", () => {
    expect(
      abilityAside(aCheck({ modifier: 3, total: 12, ability: "dex" })),
    ).toBeNull();
  });

  it("says nothing about a check against no ability at all", () => {
    expect(abilityAside(aCheck())).toBeNull();
  });
});
