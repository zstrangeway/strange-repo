"use client";

import { Minus, Plus } from "lucide-react";

import { Button } from "@gary/ui/components/button";
import { Item, ItemContent, ItemDescription, ItemTitle } from "@gary/ui/components/item";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@gary/ui/components/select";

import type { Method, Score, System } from "@/lib/api";
import {
  placed,
  priced,
  spent,
  step,
  swapped,
  worth,
  worthShowing,
} from "@/lib/scores";

// Where a character stops being a name.
//
// Which methods exist is the system's and never this page's: a list here
// would be a second place for the rules to live and the first to go stale.
// So everything below is drawn off what `/catalogue/{slug}` said — including
// whether there is anything to roll, whether the results are yours to place,
// whether the method spends a budget, what a point costs, and what a score is
// worth once it is placed.
//
// What the page *does* with them is this page's, and it is deliberately not
// novel. Arranging a set is a chooser on each ability listing the set, which
// is what every tool that has solved this does; taking one already somewhere
// trades places with it, which is the one thing those tools get wrong often
// enough to be the bug they are reported for. It was dragging before. Dragging
// wants aim and a mouse, and asks a question of your hands rather than of your
// character.

/** A score, as it reads on a sheet: the number, and what it is worth.
 *
 *  Both, because a 15 is only how the system writes down a +2, and +2 is the
 *  thing anybody is actually choosing between. What it is worth is the
 *  system's answer, never arithmetic here — first edition has a table per
 *  ability and no general modifier, and would be quietly given third
 *  edition's by anything that halved the distance from ten. */
function reads(score: number, modifiers: Record<string, number>): string {
  if (!worthShowing(modifiers)) return `${score}`;
  const each = worth(score, modifiers);
  return each === null ? `${score}` : `${score} (${each >= 0 ? "+" : ""}${each})`;
}

export default function Scores({
  system,
  method,
  onMethod,
  rolled,
  cells,
  onCells,
  scores,
  onScore,
  onStep,
  onRoll,
  rolling,
}: {
  system: System;
  method: Method | undefined;
  onMethod: (slug: string) => void;
  /** What gary produced, when the method produces anything. */
  rolled: Score[] | null;
  /** Where each of those currently sits — one cell per ability and then one
   *  for every score the system had nowhere to put. */
  cells: (number | null)[];
  onCells: (cells: (number | null)[]) => void;
  /** What is against each ability, when the numbers are not gary's. */
  scores: Record<string, number>;
  onScore: (ability: string, score: number) => void;
  /** A step up or down, which the sheet either takes or refuses. */
  onStep: (ability: string, by: number) => void;
  onRoll: () => void;
  rolling: boolean;
}) {
  const [low, high] = system.scores;
  const abilities = system.abilities;

  // Three questions the catalogue answers, and the whole of what this page
  // decides from. No method is named here.
  const arranging = !!method?.generates && method.arrange && !!rolled;
  const fixed = !!method?.generates && !method.arrange;
  const spending = !!method?.spends;

  // The table and the budget belong to the method that spends them, not to
  // every method offered by a system that happens to have one. Typing a score
  // in is not a point buy going over budget.
  const costs = spending ? system.point_costs : {};
  const budget = spending ? system.point_budget : 0;
  const paid = spent(scores, costs);
  const table = priced(costs);

  const byDice = (rolled ?? []).some((one) => one.dice.length > 0);
  const set = (rolled ?? []).map((one) => one.score);
  const sheet = arranging ? placed(cells, abilities, set) : scores;
  // What nothing is holding. The standard array is six numbers whatever a
  // system's abilities are, so a system with fewer leaves some over — said
  // plainly rather than parked in a tray, and still choosable on every row.
  const spare = cells
    .slice(abilities.length)
    .filter((held): held is number => held !== null);

  return (
    <div className="flex flex-col gap-3" data-testid="scores">
      <Select value={method?.slug} onValueChange={onMethod}>
        <SelectTrigger data-testid="method" className="w-full">
          <SelectValue placeholder="How are the scores decided?" />
        </SelectTrigger>
        <SelectContent>
          {system.methods.map((one) => (
            <SelectItem key={one.slug} value={one.slug}>
              {one.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {method ? (
        <p className="text-xs text-muted-foreground">{method.blurb}</p>
      ) : null}

      {/* A system that generates nothing says so where the choice would have
          been, rather than showing a control that does nothing. It can still
          be played — typing them in is offered everywhere. */}
      {system.cannot_generate ? (
        <p
          className="text-xs text-muted-foreground"
          data-testid="cannot-generate"
        >
          {system.cannot_generate}
        </p>
      ) : null}

      {/* Asking again is only worth offering when the answer could differ, and
          what settles that is whether dice were behind it. The standard array
          generates its six the same way every time, so it gets no button; 4d6
          and three-in-order get one. Read off what came back rather than off a
          list here of which methods are random — that would be a second place
          for the rules to live and the first to go stale. */}
      {byDice ? (
        <div className="flex items-center gap-3">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            data-testid="roll-scores"
            disabled={rolling}
            onClick={onRoll}
          >
            Roll again
          </Button>
          {/* Nobody is stopped from re-rolling: gary-api rolls it and stores
              nothing, so it costs nothing that matters, and refusing would
              only make people delete the character and start again. */}
          <span className="text-xs text-muted-foreground">
            Not what you wanted? Roll again — nothing is kept until you add
            them.
          </span>
        </div>
      ) : null}

      {budget ? (
        <p
          className={paid > budget ? "text-sm text-destructive" : "text-sm"}
          data-testid="point-spend"
        >
          {paid} of {budget} points spent
          {table.length > 0
            ? `, ${table[0]} to ${table[table.length - 1]} each`
            : ""}
        </p>
      ) : null}

      {arranging && spare.length > 0 ? (
        <p className="text-sm" data-testid="spare">
          Going spare:{" "}
          <span className="font-medium tabular-nums">
            {spare.map((held) => reads(set[held], system.modifiers)).join(", ")}
          </span>
        </p>
      ) : null}

      <div className="flex flex-col gap-2" data-testid="sheet">
        {abilities.map((ability, at) => (
          <Item key={ability} variant="muted" size="sm">
            <ItemContent>
              <ItemTitle className="uppercase">{ability}</ItemTitle>
              <ItemDescription>
                {/* Read only when the method placed them for you: three dice
                    down the page is the whole of first edition's character
                    creation and there is nothing left to decide. */}
                {fixed
                  ? "rolled in order"
                  : arranging
                    ? diceBehind(rolled, cells[at])
                    : spending
                      ? `${costs[String(sheet[ability])] ?? 0} points`
                      : `${low} to ${high}`}
              </ItemDescription>
            </ItemContent>

            {arranging ? (
              // Every score on one chooser per ability, including the ones
              // already somewhere: taking one of those is how two are swapped,
              // and leaving them out would leave no way to. `data-held` on the
              // trigger says which of the set it holds rather than which
              // number, because two dice can come to the same total and a swap
              // between two 12s has to still be a swap.
              <Select
                value={cells[at] === null ? "" : String(cells[at])}
                onValueChange={(taken) =>
                  onCells(swapped(cells, at, cells.indexOf(Number(taken))))
                }
              >
                <SelectTrigger
                  className="w-32"
                  data-testid={`score-${ability}`}
                  data-ability={ability}
                  data-score={sheet[ability]}
                  data-held={cells[at] ?? ""}
                >
                  <SelectValue placeholder="—" />
                </SelectTrigger>
                <SelectContent>
                  {set.map((one, held) => (
                    <SelectItem key={held} value={String(held)}>
                      {reads(one, system.modifiers)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : fixed ? (
              <span
                className="px-2.5 py-1 text-sm font-medium tabular-nums"
                data-testid={`score-${ability}`}
                data-ability={ability}
                data-score={sheet[ability]}
              >
                {sheet[ability] === undefined
                  ? "—"
                  : reads(sheet[ability], system.modifiers)}
              </span>
            ) : (
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  className="rounded-md border p-1 text-muted-foreground disabled:opacity-40"
                  aria-label={`Lower ${ability}`}
                  data-testid={`lower-${ability}`}
                  disabled={!step(scores, ability, -1, { costs, budget, low, high })}
                  onClick={() => onStep(ability, -1)}
                >
                  <Minus className="size-3.5" />
                </button>
                {/* A point buy has no box: what is spendable is the table's,
                    and a number typed straight in is not a spend. Typing them
                    in keeps one, because that is the whole of that method. */}
                {spending ? (
                  <span
                    className="w-16 text-center text-sm font-medium tabular-nums"
                    data-testid={`score-${ability}`}
                    data-ability={ability}
                    data-score={scores[ability]}
                  >
                    {scores[ability] === undefined
                      ? "—"
                      : reads(scores[ability], system.modifiers)}
                  </span>
                ) : (
                  <input
                    type="number"
                    className="w-16 rounded-md border bg-background px-2 py-1 text-right"
                    data-testid={`score-${ability}`}
                    data-ability={ability}
                    min={low}
                    max={high}
                    value={scores[ability] ?? ""}
                    onChange={(event) =>
                      onScore(ability, Number(event.target.value))
                    }
                  />
                )}
                <button
                  type="button"
                  className="rounded-md border p-1 text-muted-foreground disabled:opacity-40"
                  aria-label={`Raise ${ability}`}
                  data-testid={`raise-${ability}`}
                  disabled={!step(scores, ability, 1, { costs, budget, low, high })}
                  onClick={() => onStep(ability, 1)}
                >
                  <Plus className="size-3.5" />
                </button>
              </div>
            )}
          </Item>
        ))}
      </div>
    </div>
  );
}

/** The dice behind whatever this ability is holding, where there were any.
 *
 *  "15" and "6, 5, 4 and a discarded 1" are different things to read while
 *  deciding where a score goes, and they belong beside the score rather than
 *  in a list further up the page to be matched back to it by eye. */
function diceBehind(rolled: Score[] | null, held: number | null): string {
  const one = held === null ? undefined : (rolled ?? [])[held];
  if (!one || one.dropped === null) return "";
  return `${one.dice.join(" ")} − ${one.dropped}`;
}
