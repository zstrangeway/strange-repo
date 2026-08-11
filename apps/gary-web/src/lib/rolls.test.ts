import { describe, expect, it } from "vitest";

import type { Roll } from "./api";
import { workedOut } from "./rolls";

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

describe("workedOut", () => {
  it("says nothing when the total is the whole story", () => {
    // One die, nothing added: "rolled 9" beside "→ 9" is the same number
    // twice, and a turn can carry seven of these.
    expect(workedOut(aRoll())).toBeNull();
  });

  it("shows the arithmetic when something was added", () => {
    expect(
      workedOut(aRoll({ notation: "1d20+3", dice: [9], modifier: 3, total: 12 })),
    ).toBe("9 + 3 = 12");
  });

  it("shows a penalty as a subtraction rather than a negative", () => {
    // "9 + -1" is arithmetic nobody writes down.
    expect(
      workedOut(aRoll({ notation: "1d20-1", dice: [9], modifier: -1, total: 8 })),
    ).toBe("9 − 1 = 8");
  });

  it("shows every die when there was more than one", () => {
    expect(
      workedOut(aRoll({ notation: "2d6", dice: [3, 4], modifier: 0, total: 7 })),
    ).toBe("3 + 4 = 7");
  });

  it("shows dice and a modifier together", () => {
    expect(
      workedOut(aRoll({ notation: "2d6+2", dice: [3, 4], modifier: 2, total: 9 })),
    ).toBe("3 + 4 + 2 = 9");
  });

  it("says nothing about a roll with no dice at all", () => {
    // Not something gary-api sends, but a card that threw on one would take
    // the whole transcript down with it.
    expect(workedOut(aRoll({ dice: [], total: 0 }))).toBeNull();
  });
});
