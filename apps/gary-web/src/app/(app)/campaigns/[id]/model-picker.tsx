"use client";

import { ChevronsUpDown } from "lucide-react";
import { useTransition } from "react";

import { Button } from "@gary/ui/components/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@gary/ui/components/dropdown-menu";

import type { Model } from "@/lib/api";

// Which model is running this campaign, and a way to change it without
// leaving the table.
//
// Switching to something cheap while iterating and back for a session that
// matters is the whole reason the choice is exposed, so putting it behind a
// settings page would give the choice away again.
export default function ModelPicker({
  models,
  current,
  chosen,
  onPick,
}: {
  models: Model[];
  current: string;
  chosen: boolean;
  onPick: (id: string | null) => Promise<void>;
}) {
  const [pending, start] = useTransition();
  const named = models.find((model) => model.id === current);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          data-testid="model"
          disabled={pending}
        >
          <span className="text-muted-foreground">run by</span>
          {named?.name ?? current}
          {chosen ? null : (
            <span className="text-muted-foreground">(default)</span>
          )}
          <ChevronsUpDown className="size-3.5 opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="max-h-96 overflow-y-auto">
        <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
          Prices are per million tokens, in and out
        </DropdownMenuLabel>
        {models.map((model) => (
          <DropdownMenuItem
            key={model.id}
            data-testid={`use-${model.id}`}
            onSelect={() => start(() => onPick(model.id))}
          >
            <span className="flex-1">{model.name}</span>
            <span className="font-mono text-xs text-muted-foreground">
              ${model.prompt_cost.toFixed(2)} / $
              {model.completion_cost.toFixed(2)}
            </span>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          data-testid="use-default"
          onSelect={() => start(() => onPick(null))}
        >
          Whatever gary is running
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
