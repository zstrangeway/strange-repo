"use client";

import { Badge } from "@gary/ui/components/badge";
import { Item, ItemContent, ItemDescription, ItemTitle } from "@gary/ui/components/item";

import type { Roll } from "@/lib/play";

/** One thing said, and anything the engines did while it was being said. */
export type Entry = {
  id: string;
  role: "player" | "gm";
  text: string;
  rolls: Roll[];
  complete: boolean;
};

// A roll is a thing that happened, not a sentence gary wrote.
//
// Rendering it as prose would make it indistinguishable from a number gary
// made up, and the whole design rests on that distinction: gary asks, the API
// rolls, the rules grade it. So it gets its own element with the notation and
// the dice on show, and a degree beside it when the rules graded one.
function RolledDice({ roll }: { roll: Roll }) {
  return (
    <Item variant="muted" size="sm" data-testid="roll">
      <ItemContent>
        <ItemTitle className="font-mono">
          <span data-testid="roll-notation">{roll.notation}</span>
          {" → "}
          <span data-testid="roll-total">{roll.total}</span>
        </ItemTitle>
        <ItemDescription>
          {roll.reason || "a roll"}
          {roll.dc === undefined || roll.dc === null
            ? ""
            : ` against ${roll.dc}`}
          {roll.dice.length > 0 ? ` · rolled ${roll.dice.join(", ")}` : ""}
        </ItemDescription>
      </ItemContent>
      {roll.degree ? (
        <Badge variant="secondary" data-testid="roll-degree">
          {roll.degree}
        </Badge>
      ) : null}
    </Item>
  );
}

function Turn({ entry, who }: { entry: Entry; who: string }) {
  const mine = entry.role === "player";

  return (
    <div
      data-testid={mine ? "turn-player" : "turn-gm"}
      className={`flex flex-col gap-2 rounded-lg border p-4 ${
        mine ? "bg-muted/40" : ""
      }`}
    >
      <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
        {mine ? who : "gary"}
      </p>

      {entry.rolls.map((roll, index) => (
        <RolledDice key={`${entry.id}-${index}`} roll={roll} />
      ))}

      {entry.text ? (
        <p className="whitespace-pre-wrap">{entry.text}</p>
      ) : (
        // A turn that has opened but said nothing yet. Something has to be on
        // screen or the page looks like it ignored you.
        <p className="text-sm text-muted-foreground" data-testid="thinking">
          gary is thinking…
        </p>
      )}

      {entry.role === "gm" && !entry.complete && entry.text ? (
        <p className="text-xs text-muted-foreground" data-testid="incomplete">
          gary was cut off here.
        </p>
      ) : null}
    </div>
  );
}

export default function Transcript({
  entries,
  who,
}: {
  entries: Entry[];
  who: string;
}) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="nothing-said">
        Nothing has happened yet. Say what you do.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4" data-testid="transcript">
      {entries.map((entry) => (
        <Turn key={entry.id} entry={entry} who={who} />
      ))}
    </div>
  );
}
