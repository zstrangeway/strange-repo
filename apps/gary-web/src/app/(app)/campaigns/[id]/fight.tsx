"use client";

import { Badge } from "@gary/ui/components/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@gary/ui/components/card";
import { Item, ItemContent, ItemDescription, ItemTitle } from "@gary/ui/components/item";

import type { Fight, Foe, Member } from "@/lib/api";

// The fight, while there is one.
//
// Nothing here decides anything: the order was rolled by the engine and the
// position in it is folded out of the log, so this renders a fact rather than
// tracking one. That distinction is the whole reason combat was built — gary
// used to run an encounter out of whatever the last few paragraphs implied.
//
// Whose turn it is leads, because in a fight that is the only question, and
// yours is marked hardest: the others are gary's to voice and gary will move
// through them on its own, but it stops at you and waits.
export default function Fighting({
  fight,
  party,
  enemies,
}: {
  fight: Fight;
  party: Member[];
  enemies: Foe[];
}) {
  const mine = new Set(
    party.filter((one) => one.played_by === "player").map((one) => one.id),
  );
  const standing = new Map<string, { hp: number; max_hp: number; down: boolean }>(
    [...party, ...enemies].map((one) => [one.id, one]),
  );
  const up = fight.order[fight.at];

  return (
    <Card data-testid="fight">
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          <span>In a fight</span>
          <Badge variant="outline" data-testid="fight-round">
            round {fight.round}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {up && mine.has(up.id) ? (
          <p className="text-sm font-medium" data-testid="fight-yours">
            It is your turn. Say what you do.
          </p>
        ) : null}

        {fight.order.map((one, index) => {
          const state = standing.get(one.id);
          const now = index === fight.at;

          return (
            <Item
              key={one.id}
              variant={now ? "outline" : "muted"}
              size="sm"
              data-testid={`in-fight-${one.name}`}
            >
              <ItemContent>
                <ItemTitle>
                  {one.name}
                  {mine.has(one.id) ? (
                    <span className="text-muted-foreground"> · you</span>
                  ) : null}
                </ItemTitle>
                <ItemDescription>
                  {state
                    ? state.down
                      ? "down"
                      : `${state.hp}/${state.max_hp} hit points`
                    : "gone"}
                </ItemDescription>
              </ItemContent>
              {now ? (
                <Badge data-testid={`up-${one.name}`}>up</Badge>
              ) : one.side === "adversary" ? (
                <Badge variant="secondary">against you</Badge>
              ) : null}
            </Item>
          );
        })}
      </CardContent>
    </Card>
  );
}
