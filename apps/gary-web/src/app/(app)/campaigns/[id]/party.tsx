"use client";

import { useState, useTransition } from "react";

import { Badge } from "@gary/ui/components/badge";
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

import type { Member } from "@/lib/api";
import { addCharacter } from "@/lib/gary";

import { Field, Notice } from "../../../form-parts";

// Who is at the table, as they currently stand.
//
// Hit points and conditions are projected from everything that has happened
// rather than read off the sheet, so this is the world's answer and not the
// character's — which is why "why is Bramble on 3" has an answer that is a
// list of events rather than a column somebody overwrote.
export default function Party({
  campaignId,
  party,
  classes,
  loading,
  onAdded,
}: {
  campaignId: string;
  party: Member[];
  classes: string[];
  /** True until the world has been asked. Not the same as an empty party,
   *  and saying "nobody at the table" before looking is a page telling you
   *  something it does not know. */
  loading: boolean;
  onAdded: () => void;
}) {
  const [error, setError] = useState<string | undefined>(undefined);
  const [pending, start] = useTransition();

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

        <form
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const name = String(form.get("character_name") ?? "");
            const chosen = String(form.get("character_class") ?? "");
            setError(undefined);

            start(async () => {
              const result = await addCharacter(campaignId, {
                name,
                character_class: chosen,
              });
              if (result.character) {
                onAdded();
                return;
              }
              setError(result.error);
            });
          }}
        >
          <FieldGroup className="gap-3">
            <Notice error={error} />
            <Field
              label="Character name"
              name="character_name"
              placeholder="Bramble"
              labelHidden
            />
            {/* Asked of the system rather than listed here: a warlock is fine
                in a game that has warlocks and refused in one that does not,
                and gary-api refuses it either way. */}
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
              label="Add to the party"
              pending={pending}
              variant="secondary"
              data-testid="add-character"
            />
          </FieldGroup>
        </form>
      </CardContent>
    </Card>
  );
}
