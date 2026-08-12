"use client";

import { Badge } from "@gary/ui/components/badge";
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
import { spent } from "@/lib/scores";

// Where a character stops being a name.
//
// Which methods exist is the system's and never this page's: a list here
// would be a second place for the rules to live and the first to go stale.
// So everything below is drawn off what `/catalogue/{slug}` said — including
// whether there is anything to roll, whether the results are yours to place,
// and what a point costs.
export default function Scores({
  system,
  method,
  onMethod,
  rolled,
  scores,
  onScore,
  onRoll,
  rolling,
}: {
  system: System;
  method: Method | undefined;
  onMethod: (slug: string) => void;
  /** What gary produced, when the method produces anything. */
  rolled: Score[] | null;
  /** What is currently against each ability. */
  scores: Record<string, number>;
  onScore: (ability: string, score: number) => void;
  onRoll: () => void;
  rolling: boolean;
}) {
  const [low, high] = system.scores;
  const budget = system.point_budget;
  const paid = budget ? spent(scores, system.point_costs) : 0;
  const byDice = (rolled ?? []).some((one) => one.dice.length > 0);

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

      {rolled ? (
        <div className="flex flex-wrap gap-2" data-testid="rolled">
          {rolled.map((one, index) => (
            <Badge key={index} variant="outline" data-testid="rolled-score">
              {one.score}
              {one.dropped === null ? null : (
                // The dice, not just what they came to. "15" and "6, 5, 4 and
                // a discarded 1" are different things to read while you are
                // deciding where to put it.
                <span className="ml-1 font-normal text-muted-foreground">
                  ({one.dice.join(" ")} − {one.dropped})
                </span>
              )}
            </Badge>
          ))}
        </div>
      ) : null}

      {budget ? (
        <p
          className={paid > budget ? "text-sm text-destructive" : "text-sm"}
          data-testid="point-spend"
        >
          {paid} of {budget} points spent
        </p>
      ) : null}

      <div className="flex flex-col gap-2" data-testid="sheet">
        {system.abilities.map((ability) => (
          <Item key={ability} variant="muted" size="sm">
            <ItemContent>
              <ItemTitle className="uppercase">{ability}</ItemTitle>
              <ItemDescription>
                {/* Read only when the method placed them for you: three dice
                    down the page is the whole of first edition's character
                    creation and there is nothing left to decide. */}
                {method && !method.arrange
                  ? "rolled in order"
                  : `${low} to ${high}`}
              </ItemDescription>
            </ItemContent>
            <input
              type="number"
              className="w-20 rounded-md border bg-background px-2 py-1 text-right"
              data-testid={`score-${ability}`}
              min={low}
              max={high}
              readOnly={!!method && !method.arrange}
              value={scores[ability] ?? ""}
              onChange={(event) => onScore(ability, Number(event.target.value))}
            />
          </Item>
        ))}
      </div>
    </div>
  );
}
