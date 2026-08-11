// Reading a roll.
//
// Small, but here rather than beside the component that renders it, because
// `src/lib` is where the 100% gate can see it and this is the branchy part:
// which numbers are worth showing depends on how the total was reached.

import type { Roll } from "./api";

function graded(roll: Roll): boolean {
  return roll.dc !== undefined && roll.dc !== null;
}

/**
 * How the total was reached, for somebody checking it by eye.
 *
 * A **graded check always shows its faces**, even when nothing was added to
 * them. "1d20 → 12 vs 12" asks you to take on trust that the 12 was the die
 * rather than something already adjusted, and a check decided by one point is
 * exactly where that trust is worth least. It also puts a natural 20 and a
 * flat 20 on screen as different things.
 *
 * A **bare roll** stays quiet when it has nothing to add: "rolled 5" beside
 * "1d6 → 5" is the same number printed twice, and a busy turn carries seven
 * of them.
 *
 * The ability rides with the modifier it produced — "9 + 3 dex = 12" — since
 * a number is worth more with its provenance attached than beside it.
 */
export function workedOut(roll: Roll): string | null {
  if (roll.dice.length === 0) return null;

  const plain = roll.dice.length === 1 && !roll.modifier;
  if (plain && !graded(roll)) return null;

  const faces = roll.dice.join(" + ");
  if (plain) return `rolled ${faces}`;

  const sign = roll.modifier < 0 ? "−" : "+";
  const applied = roll.modifier
    ? ` ${sign} ${Math.abs(roll.modifier)}${roll.ability ? ` ${roll.ability}` : ""}`
    : "";
  return `rolled ${faces}${applied} = ${roll.total}`;
}

/**
 * The ability to show beside the reason, when the working has not said it.
 *
 * Which is only when there was no modifier to attach it to — a check against
 * dexterity that a sheet of straight tens made worth nothing is still a check
 * against dexterity, and dropping the word would lose the one part of it that
 * was not zero.
 */
export function abilityAside(roll: Roll): string | null {
  if (!roll.ability) return null;
  return roll.modifier ? null : roll.ability;
}
