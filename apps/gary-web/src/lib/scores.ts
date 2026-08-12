// Counting a point buy.
//
// Here rather than beside the component that renders it, because `src/lib` is
// where the 100% gate can see it and this is the part with branches in it: a
// score off the table costs nothing the table can say, and a sheet nobody has
// filled in yet has holes.
//
// The table itself is never here. What a score costs is the system's, and it
// arrives with the system — a copy in this app would be a second place for
// the rules to live and the first one to go stale.

/**
 * What a spread costs, under a table that says what each score is worth.
 *
 * Counted in the browser while you spend, so the number moves as you do. It
 * is a construction aid and not a gate: gary-api range-checks what finally
 * arrives, the same as it does for a score arrived at any other way, and
 * anybody determined to hand-post an illegal spread is only cheating
 * themselves.
 *
 * A score the table has no entry for costs nothing, because a table that does
 * not price something is not a table saying it is free — it is a table being
 * asked about a score from outside the method, and the range check is what
 * has an opinion about those.
 */
export function spent(
  scores: Record<string, number>,
  costs: Record<string, number>,
): number {
  return Object.values(scores).reduce(
    (total, score) => total + (costs[String(score)] ?? 0),
    0,
  );
}
