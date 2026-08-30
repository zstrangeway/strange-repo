"use client";

import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  rectSwappingStrategy,
  sortableKeyboardCoordinates,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ChevronDown, ChevronUp, GripVertical, Minus, Plus } from "lucide-react";

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
import { placed, priced, spent, step, swapped } from "@/lib/scores";

// Where a character stops being a name.
//
// Which methods exist is the system's and never this page's: a list here
// would be a second place for the rules to live and the first to go stale.
// So everything below is drawn off what `/catalogue/{slug}` said — including
// whether there is anything to roll, whether the results are yours to place,
// whether the method spends a budget, and what a point costs.
//
// What the page *does* with them is this page's, and it used to do one thing
// for all of them: print six numbers and ask you to type them into six boxes.
// The numbers were already on screen. Copying them across is not a decision
// anybody came here to make, and a digit typed wrong is a character you did
// not build. So each of the three answers the catalogue can give gets the
// control that fits it — moving what you were given, spending what you have,
// or a box for what you worked out somewhere else.

/** A cell picked up and dropped is addressed by where it sits, never by what
 *  it holds: two dice can come to the same number, and a sheet that moved
 *  values would not be able to tell one 12 from the other. */
const cellId = (at: number) => `cell:${at}`;
const cellAt = (id: string) => Number(id.slice("cell:".length));

/** One score, picked up by the mouse, a finger or the keyboard.
 *
 *  The sensors are dnd-kit's rather than mine — a hand-written version of this
 *  is where touch and keyboard quietly go missing. */
function Chip({
  score,
  dice,
  dropped,
  testId,
  ability,
  handle,
  dragging,
}: {
  score: number;
  dice: number[];
  dropped: number | null;
  testId: string;
  /** Which ability is holding it, or nothing when it is one of the spare
   *  ones — those are against no ability, which is what makes them spare. */
  ability?: string;
  /** What picks it up: the listeners, and the ref that marks the thing you
   *  actually grab. Separate from what it is dropped on — see below. */
  handle: Record<string, unknown>;
  dragging: boolean;
}) {
  return (
    <button
      type="button"
      className={`flex cursor-grab items-center gap-1.5 rounded-md border bg-background px-2.5 py-1 text-sm font-medium tabular-nums ${
        dragging ? "z-10 opacity-70 shadow-md" : ""
      }`}
      data-testid={testId}
      data-ability={ability}
      data-score={score}
      {...handle}
    >
      <GripVertical className="size-3.5 text-muted-foreground" aria-hidden />
      {score}
      {dropped === null ? null : (
        // The dice, not just what they came to. "15" and "6, 5, 4 and a
        // discarded 1" are different things to read while you decide where it
        // goes, and they belong beside the score rather than in a list further
        // up the page that has to be matched back to it by eye.
        <span className="font-normal text-muted-foreground">
          ({dice.join(" ")} − {dropped})
        </span>
      )}
    </button>
  );
}

/**
 * One ability while a set is being arranged.
 *
 * The whole row is what a score is dropped on, and only the chip is what picks
 * one up. Those are deliberately different sizes: aiming at a two-digit number
 * to drop something is a game of skill nobody asked to play, and the row is a
 * target you cannot miss.
 */
function Arranged({
  at,
  ability,
  score,
  low,
  high,
  first,
  last,
  onMove,
}: {
  at: number;
  ability: string;
  /** What is against it, or nothing when the method produced fewer scores
   *  than this system has abilities. */
  score: Score | null;
  low: number;
  high: number;
  first: boolean;
  last: boolean;
  onMove: (by: number) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: cellId(at) });

  return (
    <Item
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      variant="muted"
      size="sm"
      data-testid={`slot-${ability}`}
    >
      <ItemContent>
        <ItemTitle className="uppercase">{ability}</ItemTitle>
        <ItemDescription>
          {low} to {high}
        </ItemDescription>
      </ItemContent>
      <div className="flex items-center gap-1">
        {score === null ? (
          <span className="rounded-md border border-dashed px-2.5 py-1 text-sm text-muted-foreground">
            —
          </span>
        ) : (
          <Chip
            score={score.score}
            dice={score.dice}
            dropped={score.dropped}
            testId={`score-${ability}`}
            ability={ability}
            handle={{ ...attributes, ...listeners, ref: setActivatorNodeRef }}
            dragging={isDragging}
          />
        )}
        {/* The same swap the dragging does, for anybody who would rather press
            a button — and there is nothing above the first ability or below the
            last to swap with, so those two are not offered. */}
        <div className="flex flex-col">
          {first ? null : (
            <button
              type="button"
              className="rounded p-0.5 text-muted-foreground hover:bg-accent"
              aria-label={`Move ${ability} up`}
              data-testid={`move-up-${ability}`}
              onClick={() => onMove(-1)}
            >
              <ChevronUp className="size-4" />
            </button>
          )}
          {last ? null : (
            <button
              type="button"
              className="rounded p-0.5 text-muted-foreground hover:bg-accent"
              aria-label={`Move ${ability} down`}
              data-testid={`move-down-${ability}`}
              onClick={() => onMove(1)}
            >
              <ChevronDown className="size-4" />
            </button>
          )}
        </div>
      </div>
    </Item>
  );
}

/** A score the method had over, waiting to be brought in.
 *
 *  The chip is the whole of it — what you pick up and what is dropped on are
 *  the same thing, unlike a row, where the row is the target and the number is
 *  the handle. */
function Spare({ at, score }: { at: number; score: Score }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: cellId(at) });

  return (
    <Chip
      score={score.score}
      dice={score.dice}
      dropped={score.dropped}
      testId="spare-score"
      handle={{
        ...attributes,
        ...listeners,
        ref: setNodeRef,
        style: { transform: CSS.Transform.toString(transform), transition },
      }}
      dragging={isDragging}
    />
  );
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

  const sensors = useSensors(
    // A little travel before a drag starts, so pressing an arrow on a row is a
    // press rather than the beginning of a drag.
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    onCells(swapped(cells, cellAt(String(active.id)), cellAt(String(over.id))));
  };

  const byDice = (rolled ?? []).some((one) => one.dice.length > 0);
  const spare = cells.slice(abilities.length);
  const sheet = arranging
    ? placed(cells, abilities, (rolled ?? []).map((one) => one.score))
    : scores;

  const rows = (
    <div className="flex flex-col gap-2" data-testid="sheet">
      {abilities.map((ability, at) => {
        if (arranging) {
          const held = cells[at];
          return (
            <Arranged
              key={ability}
              at={at}
              ability={ability}
              score={held === null ? null : ((rolled ?? [])[held] ?? null)}
              low={low}
              high={high}
              first={at === 0}
              last={at === abilities.length - 1}
              onMove={(by) => onCells(swapped(cells, at, at + by))}
            />
          );
        }

        return (
          <Item key={ability} variant="muted" size="sm">
            <ItemContent>
              <ItemTitle className="uppercase">{ability}</ItemTitle>
              <ItemDescription>
                {/* Read only when the method placed them for you: three dice
                    down the page is the whole of first edition's character
                    creation and there is nothing left to decide. */}
                {fixed
                  ? "rolled in order"
                  : spending
                    ? `${costs[String(sheet[ability])] ?? 0} points`
                    : `${low} to ${high}`}
              </ItemDescription>
            </ItemContent>

            {fixed ? (
              <span
                className="px-2.5 py-1 text-sm font-medium tabular-nums"
                data-testid={`score-${ability}`}
                data-ability={ability}
                data-score={sheet[ability]}
              >
                {sheet[ability] ?? "—"}
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
                    className="w-10 text-center text-sm font-medium tabular-nums"
                    data-testid={`score-${ability}`}
                    data-ability={ability}
                    data-score={scores[ability]}
                  >
                    {scores[ability] ?? "—"}
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
        );
      })}
    </div>
  );

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

      {arranging ? (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={onDragEnd}
        >
          <SortableContext
            items={cells.map((_, at) => cellId(at))}
            // Swapping rather than shuffling everything along: dropping a 15
            // on an ability trades places with what was there, which is what
            // arranging a set of scores means. A sorting strategy would push
            // the rest of the sheet down a row to make space.
            strategy={rectSwappingStrategy}
          >
            <p className="text-xs text-muted-foreground">
              Drag a score onto another ability to swap the two, or use the
              arrows.
            </p>
            {rows}
            {/* What the method produced and the system has nowhere to put. The
                standard array is six numbers whether or not an edition has six
                abilities, and the ones over wait here rather than being
                dropped on the floor. */}
            {spare.length > 0 ? (
              <div className="flex flex-col gap-1.5" data-testid="spare">
                <p className="text-xs text-muted-foreground">
                  Spare, and yours to drag in:
                </p>
                <div className="flex flex-wrap gap-2">
                  {spare.map((held, at) =>
                    held === null ? null : (
                      <Spare
                        key={held}
                        at={abilities.length + at}
                        score={(rolled ?? [])[held]}
                      />
                    ),
                  )}
                </div>
              </div>
            ) : null}
          </SortableContext>
        </DndContext>
      ) : (
        rows
      )}
    </div>
  );
}
