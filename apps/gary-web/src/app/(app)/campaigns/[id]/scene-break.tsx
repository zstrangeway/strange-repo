"use client";

import { useState, useTransition } from "react";

import { Input } from "@gary/ui/components/input";
import { SubmitButton } from "@gary/ui/components/submit-button";

// Ending a scene by hand.
//
// Slow on purpose, and the button says so: closing a scene runs a whole pass
// through a model — reconciling what was narrated but never recorded, then
// summarising — and a control that looked instant would read as broken for
// the several seconds that takes.
export default function SceneBreak({
  disabled,
  onBreak,
}: {
  disabled?: boolean;
  onBreak: (title: string) => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [pending, start] = useTransition();

  return (
    <form
      className="flex items-center gap-2 border-t pt-4"
      onSubmit={(event) => {
        event.preventDefault();
        start(async () => {
          await onBreak(title.trim());
          setTitle("");
        });
      }}
    >
      <Input
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        placeholder="Name the next scene…"
        aria-label="Name the next scene"
        data-testid="scene-title"
        disabled={disabled || pending}
      />
      <SubmitButton
        label="Break the scene"
        pendingLabel="gary is writing the recap…"
        pending={pending}
        disabled={disabled}
        variant="secondary"
        data-testid="new-scene"
      />
    </form>
  );
}
