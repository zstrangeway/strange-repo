// Reading a roll.
//
// Small, but here rather than beside the component that renders it, because
// `src/lib` is where the 100% gate can see it and this is the branchy part:
// which numbers are worth showing depends on how the total was reached.

import type { Roll } from "./api";

/**
 * How the total was reached, when the total does not already say it.
 *
 * "rolled 9" beside "→ 9" is the same number printed twice, which is what the
 * card used to do on every unmodified roll — a column of them was mostly
 * repetition. It earns its place when something was added to the dice, or
 * when there was more than one of them.
 *
 * Null means there is nothing to show that the total has not already said.
 */
export function workedOut(roll: Roll): string | null {
  if (roll.dice.length === 0) return null;
  if (roll.dice.length === 1 && !roll.modifier) return null;

  const applied = roll.modifier
    ? ` ${roll.modifier < 0 ? "−" : "+"} ${Math.abs(roll.modifier)}`
    : "";
  return `${roll.dice.join(" + ")}${applied} = ${roll.total}`;
}
