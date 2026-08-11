"use client";

import { Badge } from "@gary/ui/components/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@gary/ui/components/card";
import { Item, ItemContent, ItemDescription, ItemTitle } from "@gary/ui/components/item";
import { Skeleton } from "@gary/ui/components/skeleton";

import Link from "next/link";

import { Button } from "@gary/ui/components/button";

import type { Member } from "@/lib/api";

// Who is at the table, as they currently stand.
//
// Hit points and conditions are projected from everything that has happened
// rather than read off the sheet, so this is the world's answer and not the
// character's — which is why "why is Bramble on 3" has an answer that is a
// list of events rather than a column somebody overwrote.
export default function Party({
  campaignId,
  party,
  loading,
}: {
  campaignId: string;
  party: Member[];
  /** True until the world has been asked. Not the same as an empty party,
   *  and saying "nobody at the table" before looking is a page telling you
   *  something it does not know. */
  loading: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>The party</CardTitle>
        <CardDescription>
          Hit points and conditions as the world currently has them.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {loading ? (
          <Skeleton className="h-12 w-full" />
        ) : party.length === 0 ? (
          <p className="text-sm text-muted-foreground" data-testid="no-party">
            Nobody at the table yet.
          </p>
        ) : (
          <div className="flex flex-col gap-2" data-testid="party">
            {party.map((member) => (
              <Item
                key={member.id}
                variant="outline"
                size="sm"
                data-testid={`member-${member.name}`}
              >
                <ItemContent>
                  <ItemTitle>{member.name}</ItemTitle>
                  <ItemDescription>
                    level {member.level} {member.character_class}
                    {member.conditions.length > 0
                      ? ` · ${member.conditions.join(", ")}`
                      : ""}
                  </ItemDescription>
                </ItemContent>
                {member.played_by === "player" ? (
                  <Badge data-testid={`plays-${member.name}`}>you</Badge>
                ) : null}
                <Badge
                  variant={member.down ? "destructive" : "secondary"}
                  data-testid="hit-points"
                >
                  {member.hp}/{member.max_hp}
                </Badge>
              </Item>
            ))}
          </div>
        )}

        {/* Making characters belongs to the step before this one, which is
            also where you change which of them is you. */}
        <Button asChild variant="ghost" size="sm">
          <Link href={`/campaigns/${campaignId}/party`}>Change the party</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
