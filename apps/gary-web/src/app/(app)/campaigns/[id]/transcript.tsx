"use client";

import { Badge } from "@gary/ui/components/badge";
import { Item, ItemContent, ItemDescription, ItemTitle } from "@gary/ui/components/item";

import type { Roll, Scene } from "@/lib/api";
import { workedOut } from "@/lib/rolls";

/** One thing said, and anything the engines did while it was being said. */
export type Entry = {
  id: string;
  role: "player" | "gm";
  text: string;
  rolls: Roll[];
  complete: boolean;
  sceneId: string;
};

// A roll is a thing that happened, not a sentence gary wrote.
//
// Rendering it as prose would make it indistinguishable from a number gary
// made up, and the whole design rests on that distinction: gary asks, the API
// rolls, the rules grade it. So it gets its own element with the notation and
// the dice on show, and a degree beside it when the rules graded one.
//
// Whose it is leads, because that was the missing piece: a turn where a party
// of four crossed a collapsing causeway showed seven numbers and no way to
// tell which neck was out. Gary was working around it by writing the name
// into the reason — "John falling damage" — where nothing could render it.
function RolledDice({ roll }: { roll: Roll }) {
  const sum = workedOut(roll);
  const graded = roll.dc !== undefined && roll.dc !== null;

  return (
    <Item variant="muted" size="sm" data-testid="roll">
      <ItemContent>
        <ItemTitle className="font-mono">
          <span data-testid="roll-notation">{roll.notation}</span>
          {" → "}
          <span data-testid="roll-total">{roll.total}</span>
          {graded ? (
            <span className="text-muted-foreground">
              {" vs "}
              <span data-testid="roll-dc">{roll.dc}</span>
            </span>
          ) : null}
        </ItemTitle>
        <ItemDescription className="flex flex-wrap items-center gap-x-1.5">
          {roll.character ? (
            <span
              className="font-medium text-foreground"
              data-testid="roll-character"
            >
              {roll.character}
            </span>
          ) : null}
          <span>{roll.reason || "a roll"}</span>
          {roll.ability ? (
            <span data-testid="roll-ability">· {roll.ability}</span>
          ) : null}
          {sum ? (
            <span className="font-mono" data-testid="roll-sum">
              · {sum}
            </span>
          ) : null}
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

// The seam, drawn where gary's memory has one.
//
// Above a boundary is the story; below it is what gary is actually working
// from. A closed scene shows its recap because that recap is now the whole of
// what gary remembers of it — so what is on screen is what gary has, which is
// the only honest way to render this.
function Break({ scene }: { scene: Scene }) {
  return (
    <div className="flex flex-col gap-2 pt-2" data-testid="scene-break">
      <div className="flex items-center gap-3">
        <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          Scene {scene.number}
        </span>
        <span className="font-medium" data-testid="scene-title">
          {scene.title || "Untitled"}
        </span>
        {scene.open ? <Badge variant="secondary">playing</Badge> : null}
        <span className="h-px flex-1 bg-border" />
      </div>

      {!scene.open ? (
        <p
          className="text-sm text-muted-foreground italic"
          data-testid="scene-recap"
        >
          {scene.recap ??
            "gary could not be reached to say what happened in this scene."}
        </p>
      ) : null}
    </div>
  );
}

export default function Transcript({
  entries,
  scenes,
  who,
}: {
  entries: Entry[];
  scenes: Scene[];
  who: string;
}) {
  if (entries.length === 0 && scenes.length <= 1) {
    return (
      // Not "say what you do": nothing has happened for anyone to react to
      // yet, and the opening is on its way.
      <p className="text-sm text-muted-foreground" data-testid="nothing-said">
        gary is setting the scene…
      </p>
    );
  }

  // Grouped by scene rather than laid out flat, and in the scenes' own order
  // rather than the turns'. A scene with nothing in it still shows — an empty
  // scene is a fact about the campaign, not an absence of one.
  const known = new Set(scenes.map((scene) => scene.id));

  return (
    <div className="flex flex-col gap-4" data-testid="transcript">
      {scenes.map((scene) => (
        <div key={scene.id} className="flex flex-col gap-4">
          {/* Only worth drawing when there is more than one. A campaign that
              has never broken a scene has no seam to show. */}
          {scenes.length > 1 ? <Break scene={scene} /> : null}
          {entries
            .filter((entry) => entry.sceneId === scene.id)
            .map((entry) => (
              <Turn key={entry.id} entry={entry} who={who} />
            ))}
        </div>
      ))}

      {/* Anything whose scene the page has not caught up with yet — a turn
          said in a scene opened by the stream a moment ago. Rendered rather
          than dropped: a turn that vanishes because bookkeeping lagged is
          worse than one in slightly the wrong place. */}
      {entries
        .filter((entry) => !known.has(entry.sceneId))
        .map((entry) => (
          <Turn key={entry.id} entry={entry} who={who} />
        ))}
    </div>
  );
}
