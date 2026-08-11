"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@gary/ui/components/badge";
import { Button } from "@gary/ui/components/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@gary/ui/components/empty";
import { Item, ItemContent, ItemDescription, ItemTitle } from "@gary/ui/components/item";
import { Skeleton } from "@gary/ui/components/skeleton";

import { myCampaigns } from "@/lib/gary";
import type { Campaign } from "@/lib/api";

// Where signing in lands you. The empty state is a new account's first
// screen, so it has to lead somewhere rather than only report that there is
// nothing here.
export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);

  const load = useCallback(async () => {
    setCampaigns(await myCampaigns());
  }, []);

  useEffect(() => {
    // Fetching on mount, which is what an effect is for.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-semibold tracking-tight">
            Your campaigns
          </h1>
          <p className="text-sm text-muted-foreground">
            Gary runs the game. You decide what your characters do.
          </p>
        </div>
        {campaigns && campaigns.length > 0 ? (
          <Button asChild>
            <Link href="/campaigns/new">Start a campaign</Link>
          </Button>
        ) : null}
      </div>

      {campaigns === null ? (
        <div className="flex flex-col gap-3" data-testid="campaigns-loading">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : campaigns.length === 0 ? (
        <Empty data-testid="no-campaigns">
          <EmptyHeader>
            <EmptyMedia variant="icon">🎲</EmptyMedia>
            <EmptyTitle>No campaigns yet</EmptyTitle>
            <EmptyDescription>
              Pick a system and a module, make a character, and gary will take
              it from there.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button asChild>
              <Link href="/campaigns/new">Start your first campaign</Link>
            </Button>
          </EmptyContent>
        </Empty>
      ) : (
        <ul className="flex flex-col gap-3" data-testid="campaigns">
          {campaigns.map((campaign) => (
            <li key={campaign.id}>
              <Link href={`/campaigns/${campaign.id}`} className="block">
                <Item variant="outline" className="hover:bg-accent">
                  <ItemContent>
                    <ItemTitle>{campaign.name}</ItemTitle>
                    <ItemDescription>
                      {campaign.title} · {campaign.turns}{" "}
                      {campaign.turns === 1 ? "turn" : "turns"}
                    </ItemDescription>
                  </ItemContent>
                  <Badge variant="secondary">{campaign.model}</Badge>
                </Item>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
