"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, useTransition } from "react";

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
import { Skeleton } from "@gary/ui/components/skeleton";
import { SubmitButton } from "@gary/ui/components/submit-button";

import type { Model, Module, System } from "@/lib/api";
import { catalogue, runnableModels, startCampaign } from "@/lib/gary";

import { Field, Notice } from "../../../form-parts";

// Starting a campaign, in steps rather than in four dropdowns.
//
// The module list is a consequence of the system, so a form with both on
// screen at once can be filled in with a pairing gary-api refuses
// (`no_such_module`). Steps make that combination unreachable rather than
// merely rejected.

/** A row you can pick, in any of the steps. The label is the accessible name
 *  outright, so what a spec clicks is what a person reads. */
function Choice({
  label,
  description,
  badge,
  testId,
  onPick,
}: {
  label: string;
  description: string;
  badge?: React.ReactNode;
  testId: string;
  onPick: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      data-testid={testId}
      onClick={onPick}
      className="w-full cursor-pointer text-left"
    >
      <Item variant="outline" className="hover:bg-accent">
        <ItemContent>
          <ItemTitle>{label}</ItemTitle>
          <ItemDescription>{description}</ItemDescription>
        </ItemContent>
        {badge}
      </Item>
    </button>
  );
}

/** A step that has been answered: what was picked, and a way back to it. */
function Chosen({
  what,
  onChange,
}: {
  what: string;
  onChange: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <p className="text-sm font-medium">{what}</p>
      <Button type="button" variant="ghost" size="sm" onClick={onChange}>
        Change
      </Button>
    </div>
  );
}

function money(dollars: number) {
  return `$${dollars.toFixed(2)}`;
}

export default function NewCampaignPage() {
  const router = useRouter();

  const [systems, setSystems] = useState<System[] | null>(null);
  const [models, setModels] = useState<Model[] | null>(null);

  const [system, setSystem] = useState<System | null>(null);
  const [module, setModule] = useState<Module | null>(null);
  // Undefined means "not answered yet"; null means "answered, with whatever
  // the deployment runs". They are different states and the step after this
  // one only appears for one of them.
  const [model, setModel] = useState<Model | null | undefined>(undefined);

  const [error, setError] = useState<string | undefined>(undefined);
  const [pending, start] = useTransition();

  const load = useCallback(async () => {
    const [offered, runnable] = await Promise.all([
      catalogue(),
      runnableModels(),
    ]);
    setSystems(offered);
    setModels(runnable);
  }, []);

  useEffect(() => {
    // Fetching on mount, which is what an effect is for.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  function pickSystem(chosen: System) {
    setSystem(chosen);
    // The module belonged to the old system, so it cannot survive the change.
    setModule(null);
    setModel(undefined);
  }

  function submit(name: string) {
    if (!system || !module) {
      return;
    }

    // Caught here rather than at gary-api: a blank name is not worth a round
    // trip, and the answer that comes back is a validation payload rather
    // than a sentence.
    if (!name.trim()) {
      setError("A campaign needs a name");
      return;
    }

    start(async () => {
      const result = await startCampaign({
        name: name.trim(),
        system: system.slug,
        module: module.slug,
        model: model?.id ?? null,
      });

      if (result.campaign) {
        router.push(`/campaigns/${result.campaign.id}`);
        return;
      }
      setError(result.error);
    });
  }

  const suggested = (models ?? []).filter((one) => one.suggested);
  const rest = (models ?? []).filter((one) => !one.suggested);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">
          Start a campaign
        </h1>
        <p className="text-sm text-muted-foreground">
          A system, an adventure written for it, and a model to run it.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Which system?</CardTitle>
          <CardDescription>
            The rules gary is bound by — what a check is, and how many ways it
            can go.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {system ? (
            <Chosen
              what={system.name}
              onChange={() => {
                setSystem(null);
                setModule(null);
                setModel(undefined);
              }}
            />
          ) : systems === null ? (
            <Skeleton className="h-16 w-full" />
          ) : (
            <div className="flex flex-col gap-3" data-testid="systems">
              {systems.map((one) => (
                <Choice
                  key={one.slug}
                  label={one.name}
                  description={one.blurb}
                  badge={
                    <Badge variant="secondary">
                      {one.degrees.length} degrees
                    </Badge>
                  }
                  testId={`system-${one.slug}`}
                  onPick={() => pickSystem(one)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {system ? (
        <Card>
          <CardHeader>
            <CardTitle>Which adventure?</CardTitle>
            <CardDescription>
              Written for {system.name}. Gary starts you where it starts.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {module ? (
              <Chosen
                what={module.title}
                onChange={() => {
                  setModule(null);
                  setModel(undefined);
                }}
              />
            ) : (
              <div className="flex flex-col gap-3" data-testid="modules">
                {system.modules.map((one) => (
                  <Choice
                    key={one.slug}
                    label={one.title}
                    description={one.premise}
                    testId={`module-${one.slug}`}
                    onPick={() => setModule(one)}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

      {system && module ? (
        <Card>
          <CardHeader>
            <CardTitle>Which model should run it?</CardTitle>
            <CardDescription>
              Prices are per million tokens, in and out. They differ by two
              orders of magnitude, which is the whole reason this is a choice
              rather than a setting. The suggestions come from price and
              reputation, not from evidence — see how one does and move the
              campaign if it disappoints.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {model !== undefined ? (
              <Chosen
                what={model ? model.name : "Whatever gary is running"}
                onChange={() => setModel(undefined)}
              />
            ) : models === null ? (
              <Skeleton className="h-16 w-full" />
            ) : (
              <div className="flex flex-col gap-3" data-testid="models">
                {[...suggested, ...rest].map((one) => (
                  <Choice
                    key={one.id}
                    label={one.name}
                    description={one.id}
                    badge={
                      <div className="flex items-center gap-2">
                        {one.reasons ? (
                          <Badge variant="outline">reasons</Badge>
                        ) : null}
                        {one.suggested ? <Badge>suggested</Badge> : null}
                        <span
                          data-testid="model-price"
                          className="font-mono text-xs text-muted-foreground"
                        >
                          {money(one.prompt_cost)} / {money(one.completion_cost)}
                        </span>
                      </div>
                    }
                    testId={`model-${one.id}`}
                    onPick={() => setModel(one)}
                  />
                ))}
                <Choice
                  label="Whatever gary is running"
                  description="Follows the deployment's default, whatever that becomes."
                  testId="model-default"
                  onPick={() => setModel(null)}
                />
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

      {system && module && model !== undefined ? (
        <Card>
          <CardHeader>
            <CardTitle>What is it called?</CardTitle>
            <CardDescription>
              Yours to name — the module keeps its own title.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form
              noValidate
              onSubmit={(event) => {
                event.preventDefault();
                const name = new FormData(event.currentTarget).get("name");
                setError(undefined);
                submit(typeof name === "string" ? name : "");
              }}
            >
              <FieldGroup className="gap-4">
                <Notice error={error} />
                <Field
                  label="Campaign name"
                  name="name"
                  defaultValue={module.title}
                  labelHidden
                />
                <SubmitButton label="Start the campaign" pending={pending} />
              </FieldGroup>
            </form>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
