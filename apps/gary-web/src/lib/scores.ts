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

/**
 * Where a generated set sits while you arrange it.
 *
 * One cell per ability, in the system's order, and then a cell for every score
 * the system had nowhere to put — the standard array is six numbers whether or
 * not the edition has six abilities, so what does not fit has to wait
 * somewhere rather than be dropped on the floor.
 *
 * Cells hold the *position* of a score in what came back, never the score
 * itself. Two dice can come to the same number, and a sheet that moved values
 * around could not tell one 12 from the other — which is a swap that silently
 * does nothing, and the hardest kind of nothing to notice.
 */
export function arrange(rolled: number, abilities: number): (number | null)[] {
  return Array.from({ length: Math.max(rolled, abilities) }, (_, at) =>
    at < rolled ? at : null,
  );
}

/**
 * The same cells with two of them exchanged.
 *
 * One operation for every way of moving a score, because they are all the same
 * move: an arrow swaps a cell with its neighbour, a drag swaps the cell picked
 * up with the one it was dropped on, and dragging a spare score in swaps it
 * with whatever was holding that ability — which is what makes the displaced
 * score wait rather than vanish.
 *
 * A position that is not there leaves the sheet alone. Nothing on the page
 * offers such a move, but the alternative to checking is a hole punched in the
 * sheet by an id that arrived from somewhere unexpected.
 */
export function swapped(
  cells: (number | null)[],
  one: number,
  two: number,
): (number | null)[] {
  if (!(one in cells) || !(two in cells)) return cells;
  const moved = [...cells];
  moved[one] = cells[two];
  moved[two] = cells[one];
  return moved;
}

/**
 * What the arrangement comes to: a score against each ability holding one.
 *
 * Cells past the last ability are the spare ones and are not on the sheet, and
 * an ability holding nothing is left out rather than sent as a zero — a system
 * with more abilities than the method produced scores for has genuine holes,
 * and gary-api fills those with the system's own default.
 */
export function placed(
  cells: (number | null)[],
  abilities: string[],
  rolled: number[],
): Record<string, number> {
  const sheet: Record<string, number> = {};
  cells.forEach((held, at) => {
    const ability = abilities[at];
    if (ability === undefined || held === null) return;
    sheet[ability] = rolled[held];
  });
  return sheet;
}

/** Every score a cost table prices, lowest first. Empty when there is none. */
export function priced(costs: Record<string, number>): number[] {
  return Object.keys(costs)
    .map(Number)
    .sort((one, two) => one - two);
}

/**
 * What a point buy starts from: every ability at the cheapest score priced.
 *
 * A spend begins legal and stays legal, rather than beginning as six holes
 * that have to be filled before the total means anything. Nothing when the
 * system prices nothing, because then there is no spending to start.
 */
export function cheapest(
  abilities: string[],
  costs: Record<string, number>,
): Record<string, number> {
  const table = priced(costs);
  if (table.length === 0) return {};
  return Object.fromEntries(abilities.map((one) => [one, table[0]]));
}

/** What the arrows are allowed to do to one ability. */
export type Rules = {
  /** What each score costs, when the method spends. Empty when it does not —
   *  the table belongs to the point buy, not to every method in a system that
   *  happens to have one. */
  costs: Record<string, number>;
  /** What there is to spend, or 0 when nothing is being spent. */
  budget: number;
  /** The lowest and highest score the system allows. */
  low: number;
  high: number;
};

/**
 * Where a step up or down lands, or null when there is nowhere for it to go.
 *
 * One function for the arrows and for whether to offer them: a disabled arrow
 * and a refused press are the same question asked twice, and asking it in two
 * places is how they come to disagree.
 *
 * Under a cost table the steps walk the table, so a point buy cannot reach a
 * score the edition does not price, and cannot walk past what the budget will
 * carry. Without one they are worth a point either way, bounded by what the
 * system allows — which is what a score worked out at a real table needs, and
 * why the table is not passed in for that.
 */
export function step(
  scores: Record<string, number>,
  ability: string,
  by: number,
  rules: Rules,
): Record<string, number> | null {
  const now = scores[ability];
  // Nothing to step from. Guessing a number for an empty box would be putting
  // a score on the sheet that nobody chose.
  if (now === undefined) return null;

  const table = priced(rules.costs);
  let next: number;
  if (table.length > 0) {
    const at = table.indexOf(now);
    // Off the table altogether: the steps walk the table, and a score it does
    // not price is not somewhere on it to walk from.
    if (at < 0) return null;
    next = table[at + by];
    // Ran off one end of it.
    if (next === undefined) return null;
  } else {
    next = now + by;
    if (next < rules.low || next > rules.high) return null;
  }

  const wanted = { ...scores, [ability]: next };
  // A wall rather than a warning, which is the difference between an arrow and
  // a box: an arrow that cannot be paid for is simply not offered, while a
  // number typed into a box is shown going over and left to be argued with.
  if (rules.budget > 0 && spent(wanted, rules.costs) > rules.budget) return null;
  return wanted;
}
