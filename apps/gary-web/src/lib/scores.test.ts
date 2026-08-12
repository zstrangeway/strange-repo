import { describe, expect, it } from "vitest";

import { spent } from "./scores";

// The fifth edition table, as it arrives from the system. Written out here
// rather than imported, so a change to the rules has to be made deliberately
// in the system rather than agreed with silently by a test.
const COSTS = { 8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9 };

describe("spent", () => {
  it("costs nothing before anything is placed", () => {
    expect(spent({}, COSTS)).toBe(0);
  });

  it("adds up what each score is worth", () => {
    // 15, 14, 13, 12, 10, 8 — the standard array, which is what 27 points is
    // meant to be roughly worth.
    expect(
      spent(
        { str: 15, dex: 14, con: 13, int: 12, wis: 10, cha: 8 },
        COSTS,
      ),
    ).toBe(9 + 7 + 5 + 4 + 2 + 0);
  });

  it("charges nothing for a score the table does not price", () => {
    // Not a table saying an 18 is free — it is a table being asked about a
    // score from outside the method, and the range check is what has an
    // opinion about those.
    expect(spent({ str: 18 }, COSTS)).toBe(0);
  });

  it("counts nothing when there is no table", () => {
    expect(spent({ str: 15 }, {})).toBe(0);
  });
});
