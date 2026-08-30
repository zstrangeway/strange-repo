import { describe, expect, it } from "vitest";

import {
  arrange,
  cheapest,
  placed,
  priced,
  spent,
  step,
  swapped,
} from "./scores";

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

describe("arrange", () => {
  it("puts every score somewhere, in the order it came back", () => {
    expect(arrange(3, 3)).toEqual([0, 1, 2]);
  });

  it("keeps what the system had nowhere to put", () => {
    // The standard array is six numbers whether or not the edition has six
    // abilities. The three that do not fit wait rather than disappear.
    expect(arrange(6, 3)).toEqual([0, 1, 2, 3, 4, 5]);
  });

  it("leaves an ability empty when the method produced fewer", () => {
    expect(arrange(2, 4)).toEqual([0, 1, null, null]);
  });
});

describe("swapped", () => {
  it("exchanges two cells", () => {
    expect(swapped([0, 1, 2], 0, 2)).toEqual([2, 1, 0]);
  });

  it("exchanges a placed score with an empty cell", () => {
    expect(swapped([0, null], 0, 1)).toEqual([null, 0]);
  });

  it("leaves the sheet alone when a cell is not there", () => {
    const cells = [0, 1];
    expect(swapped(cells, 0, 7)).toBe(cells);
    expect(swapped(cells, -1, 1)).toBe(cells);
  });
});

describe("placed", () => {
  it("reads a score off each ability", () => {
    expect(placed([1, 0], ["str", "dex"], [15, 8])).toEqual({
      str: 8,
      dex: 15,
    });
  });

  it("leaves the spare ones off the sheet", () => {
    // Cells past the last ability are what the method had over.
    expect(placed([0, 1, 2], ["str"], [15, 14, 13])).toEqual({ str: 15 });
  });

  it("leaves an ability holding nothing out entirely", () => {
    // Not sent as a zero: a hole is gary-api's to fill with the system's own
    // default, and a zero is a score somebody chose.
    expect(placed([0, null], ["str", "dex"], [15])).toEqual({ str: 15 });
  });
});

describe("priced", () => {
  it("reads the table lowest first", () => {
    expect(priced({ 10: 2, 8: 0, 9: 1 })).toEqual([8, 9, 10]);
  });

  it("is empty when the system prices nothing", () => {
    expect(priced({})).toEqual([]);
  });
});

describe("cheapest", () => {
  it("starts every ability at the bottom of the table", () => {
    expect(cheapest(["str", "dex"], COSTS)).toEqual({ str: 8, dex: 8 });
  });

  it("starts nothing when there is no table", () => {
    expect(cheapest(["str"], {})).toEqual({});
  });
});

describe("step", () => {
  // What a point buy is bounded by, and what typing them in is not.
  const BUYING = { costs: COSTS, budget: 27, low: 3, high: 18 };
  const TYPING = { costs: {}, budget: 0, low: 3, high: 18 };

  it("walks the table a score at a time", () => {
    expect(step({ str: 8 }, "str", 1, BUYING)).toEqual({ str: 9 });
    expect(step({ str: 9 }, "str", -1, BUYING)).toEqual({ str: 8 });
  });

  it("stops at both ends of the table", () => {
    expect(step({ str: 8 }, "str", -1, BUYING)).toBe(null);
    expect(step({ str: 15 }, "str", 1, BUYING)).toBe(null);
  });

  it("refuses a step the budget cannot carry", () => {
    // Three 15s is 27 of 27 spent, so the cheapest step anywhere else — an 8
    // to a 9, which is one point — is one the budget cannot carry.
    const spent_out = { str: 15, dex: 15, con: 15, int: 8, wis: 8, cha: 8 };
    expect(step(spent_out, "int", 1, BUYING)).toBe(null);
    // A point short of that, and the same step goes through.
    expect(step({ ...spent_out, con: 14 }, "int", 1, BUYING)).toEqual({
      ...spent_out,
      con: 14,
      int: 9,
    });
  });

  it("refuses to step a score the table does not price", () => {
    // An 18 arrived from somewhere that was not this table, and the arrows
    // walk the table.
    expect(step({ str: 18 }, "str", -1, BUYING)).toBe(null);
  });

  it("is worth a point either way when nothing is priced", () => {
    expect(step({ dex: 16 }, "dex", 1, TYPING)).toEqual({ dex: 17 });
    expect(step({ dex: 16 }, "dex", -1, TYPING)).toEqual({ dex: 15 });
  });

  it("stops at what the system allows", () => {
    expect(step({ dex: 18 }, "dex", 1, TYPING)).toBe(null);
    expect(step({ dex: 3 }, "dex", -1, TYPING)).toBe(null);
  });

  it("has nowhere to step from an empty box", () => {
    expect(step({}, "dex", 1, TYPING)).toBe(null);
  });
});
