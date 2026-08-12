"use client";

import { useRouter } from "next/navigation";
import { use, useCallback, useEffect, useState, useTransition } from "react";

import { Badge } from "@gary/ui/components/badge";
import { Button } from "@gary/ui/components/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@gary/ui/components/card";
import { FieldGroup } from "@gary/ui/components/field";
import { Item, ItemContent, ItemDescription, ItemTitle } from "@gary/ui/components/item";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@gary/ui/components/select";
import { Skeleton } from "@gary/ui/components/skeleton";
import { SubmitButton } from "@gary/ui/components/submit-button";

import type { Campaign, Character, Score, System } from "@/lib/api";
import {
  addCharacter,
  campaign as readCampaign,
  partyOf,
  rollScores,
  systemNamed,
  takeOver,
} from "@/lib/gary";

import Scores from "./scores";

import { Field, Notice } from "../../../../form-parts";

// Building the party, before the table rather than beside it.
//
// It used to happen on the campaign page, which meant that page loaded with
// nothing on it, a disabled composer, and "gary is setting the scene" while
// gary was doing nothing of the sort — because there was nobody to set it
// for. A screen that cannot proceed should be about the thing it is waiting
// for, and this is that thing.
//
// One character is yours. The rest are companions: gary speaks for them and
// you may tell them what to do.
export default function PartyPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [party, setParty] = useState<Character[] | null>(null);
  const [system, setSystem] = useState<System | null>(null);
  // Which method, what gary produced by it, and where the numbers currently
  // sit. Held here rather than in the score step because the form below
  // submits them, and two components owning one sheet is one too many.
  const [method, setMethod] = useState<string>("");
  const [rolled, setRolled] = useState<Score[] | null>(null);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [rolling, setRolling] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);
  const [pending, start] = useTransition();

  const load = useCallback(async () => {
    const found = await readCampaign(id);
    if (!found) {
      router.replace("/");
      return;
    }

    const [here, found_system] = await Promise.all([
      partyOf(id),
      systemNamed(found.system),
    ]);
    setCampaign(found);
    setParty(here);
    setSystem(found_system ?? null);
    // The first one the system lists, which is the one to take if you do not
    // care. Never a name this app knows.
    setMethod(found_system?.methods[0]?.slug ?? "");
  }, [id, router]);

  useEffect(() => {
    // Fetching on mount, which is what an effect is for.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const chosen = system?.methods.find((one) => one.slug === method);
  const classes = system?.classes ?? [];

  // What a generating method produces arrives without being asked for. The
  // standard array is a fixed six numbers: there is nothing to decide about
  // fetching it, and a button to fetch it again would hand back the same six.
  // Whether it can usefully be asked for a second time is a different
  // question, and the answer is in what came back — see the score step.
  useEffect(() => {
    if (!chosen?.generates) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setRolled(null);
      return;
    }

    let live = true;
    void (async () => {
      const result = await rollScores(id, chosen.slug);
      if (!live) return;
      if (!result.rolled) {
        setError(result.error);
        return;
      }
      setRolled(result.rolled.scores);
      // Placed already when the method does not let you arrange them, and
      // left for you when it does.
      setScores(result.rolled.assigned ?? {});
    })();

    // A method switched away from mid-flight must not land on the new one.
    return () => {
      live = false;
    };
  }, [id, chosen?.generates, chosen?.slug]);

  if (!campaign || party === null || !system) {
    return <Skeleton className="h-64 w-full" data-testid="party-loading" />;
  }

  const mine = party.find((one) => one.played_by === "player");

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">
          {campaign.name}
        </h1>
        <p className="text-sm text-muted-foreground">
          Who is going, and which of them is you.
        </p>
      </div>

      {/* What you are walking into, before anybody has been made. */}
      <div
        className="rounded-lg border border-dashed p-4"
        data-testid="premise"
      >
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          {campaign.title}
        </p>
        <p className="mt-1 text-sm">{campaign.premise}</p>
        <p className="mt-2 text-sm" data-testid="hook">
          {campaign.hook}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>The party</CardTitle>
          <CardDescription>
            You play one of them. Gary speaks for the rest, and you can tell
            them what to do.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {party.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="no-party">
              Nobody yet. Make the character you want to be.
            </p>
          ) : (
            <div className="flex flex-col gap-2" data-testid="party">
              {party.map((character) => (
                <Item
                  key={character.id}
                  variant="outline"
                  size="sm"
                  data-testid={`member-${character.name}`}
                >
                  <ItemContent>
                    <ItemTitle>{character.name}</ItemTitle>
                    <ItemDescription>
                      level {character.level} {character.character_class} ·{" "}
                      {character.max_hp}/{character.max_hp}
                    </ItemDescription>
                  </ItemContent>
                  {character.played_by === "player" ? (
                    <Badge data-testid={`plays-${character.name}`}>you</Badge>
                  ) : (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      data-testid={`take-over-${character.name}`}
                      disabled={pending}
                      onClick={() =>
                        start(async () => {
                          const result = await takeOver(id, character.id);
                          if (result.party) {
                            setParty(result.party);
                            return;
                          }
                          setError(result.error);
                        })
                      }
                    >
                      <span
                        className="text-muted-foreground"
                        data-testid={`plays-${character.name}`}
                      >
                        gary plays them
                      </span>
                    </Button>
                  )}
                </Item>
              ))}
            </div>
          )}

          <form
            noValidate
            onSubmit={(event) => {
              event.preventDefault();
              const form = new FormData(event.currentTarget);
              const shape = {
                name: String(form.get("character_name") ?? ""),
                character_class: String(form.get("character_class") ?? ""),
                // Only what has actually been placed. Nobody has to arrange
                // six numbers to play, and a campaign started before this
                // existed has characters who never did.
                abilities:
                  Object.keys(scores).length > 0 ? scores : undefined,
                // The first one is you unless you already are somebody. No
                // choosing between two buttons for a decision that only has
                // one sensible answer at the time it is made.
                mine: !mine,
              };
              setError(undefined);
              event.currentTarget.reset();

              start(async () => {
                const result = await addCharacter(id, shape);
                if (result.character) {
                  setParty(await partyOf(id));
                  // Cleared for the next one: a companion arranged from the
                  // last character's leftovers would be the same person twice.
                  setScores({});
                  setRolled(null);
                  return;
                }
                setError(result.error);
              });
            }}
          >
            <FieldGroup className="gap-3">
              <Notice error={error} />
              <Scores
                system={system}
                method={chosen}
                onMethod={(slug) => {
                  setMethod(slug);
                  // What the last method produced is not what this one would.
                  setRolled(null);
                  setScores({});
                }}
                rolled={rolled}
                scores={scores}
                onScore={(ability, score) =>
                  setScores((held) => ({ ...held, [ability]: score }))
                }
                rolling={rolling}
                onRoll={() =>
                  start(async () => {
                    setRolling(true);
                    const result = await rollScores(id, method);
                    setRolling(false);
                    if (!result.rolled) {
                      setError(result.error);
                      return;
                    }
                    setRolled(result.rolled.scores);
                    // Placed already when the method does not let you
                    // arrange them, and left for you when it does.
                    setScores(result.rolled.assigned ?? {});
                  })
                }
              />
              <Field
                label="Character name"
                name="character_name"
                placeholder={mine ? "A companion" : "The one you play"}
                labelHidden
              />
              <Select name="character_class" defaultValue={classes[0]}>
                <SelectTrigger data-testid="character-class" className="w-full">
                  <SelectValue placeholder="Class" />
                </SelectTrigger>
                <SelectContent>
                  {classes.map((name) => (
                    <SelectItem key={name} value={name}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <SubmitButton
                label={mine ? "Add a companion" : "This one is me"}
                pending={pending}
                variant="secondary"
                data-testid="add-character"
              />
            </FieldGroup>
          </form>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          {mine
            ? `You are ${mine.name}.`
            : "Nobody here is you yet, so there is nobody to be."}
        </p>
        <Button
          data-testid="take-them-in"
          disabled={!mine}
          onClick={() => router.push(`/campaigns/${id}`)}
        >
          Take them in
        </Button>
      </div>
    </div>
  );
}
