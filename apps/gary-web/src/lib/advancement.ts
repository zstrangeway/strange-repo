// Reading advancement.
//
// Here rather than beside the components, for `rolls.ts`'s reason: `src/lib`
// is where the 100% gate can see it, and the branchy part is what a card can
// honestly say when there is no next number to reach.

import type { Member, WorldChange } from "./api";

/** An award as it arrived, once it is known to be one. */
export type Award = {
  character: string;
  amount: number;
  reason: string;
};

/** A level, which is the engine's answer to an award rather than gary's. */
export type Level = {
  character: string;
  level: number;
  hit_points: number;
};

/**
 * How far along somebody is, for a card.
 *
 * Null when there is no next level to reach. Two different silences answer
 * the same way on purpose: somebody at the top of a system that prices
 * levels, and anybody at all in a system that does not price them, both have
 * no number coming — and a card has the same thing to say about each.
 */
export function progress(
  member: Pick<Member, "experience" | "next_level">,
): { have: number; needed: number; fraction: number } | null {
  if (member.next_level === null) return null;
  const needed = member.next_level;
  // A campaign that predates any of this, or a table whose first level costs
  // nothing: dividing would be a zero denominator, and "0 of 0" is not a
  // thing to put on screen.
  if (needed <= 0) return null;
  const have = Math.min(member.experience, needed);
  return { have, needed, fraction: have / needed };
}

/** An award, if that is what this change is. */
export function asAward(change: WorldChange): Award | null {
  if (change.kind !== "experience-gained") return null;
  return {
    character: String(change.character ?? ""),
    amount: Number(change.amount ?? 0),
    reason: String(change.reason ?? ""),
  };
}

/** A level, if that is what this change is. */
export function asLevel(change: WorldChange): Level | null {
  if (change.kind !== "level-gained") return null;
  return {
    character: String(change.character ?? ""),
    level: Number(change.level ?? 0),
    hit_points: Number(change.hit_points ?? 0),
  };
}

/**
 * What an award reads as on the table.
 *
 * The reason is what makes a column of numbers legible — "300 experience" is
 * a number and "300 experience for the mud creature" is something that
 * happened — so it is only left off when there is genuinely none.
 */
export function readAward(award: Award): string {
  const gained = `${award.character} gained ${award.amount} experience`;
  return award.reason ? `${gained} for ${award.reason}` : gained;
}

/** What a level reads as. The hit points come with it, because they are the
 *  part the engine rolled and the part a player wants to see. */
export function readLevel(level: Level): string {
  return (
    `${level.character} reached level ${level.level}` +
    `, and ${level.hit_points} hit points with it`
  );
}
