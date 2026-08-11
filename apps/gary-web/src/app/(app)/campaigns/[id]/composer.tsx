"use client";

import { useRef } from "react";

import { SubmitButton } from "@gary/ui/components/submit-button";
import { Textarea } from "@gary/ui/components/textarea";

// Saying what you do.
//
// Disabled while gary is answering, which is not politeness: a second turn
// sent mid-stream would be narrated against a transcript that does not yet
// contain the first one, and the two answers would contradict each other.
export default function Composer({
  busy,
  disabled,
  hint,
  onSay,
}: {
  busy: boolean;
  disabled?: boolean;
  hint?: string;
  onSay: (message: string) => void;
}) {
  const field = useRef<HTMLTextAreaElement>(null);

  function say() {
    const message = field.current?.value.trim() ?? "";
    if (!message) {
      return;
    }
    if (field.current) {
      field.current.value = "";
    }
    onSay(message);
  }

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        say();
      }}
    >
      <Textarea
        ref={field}
        name="message"
        rows={3}
        data-testid="composer"
        disabled={busy || disabled}
        placeholder={hint ?? "I push open the door…"}
        aria-label="What do you do?"
        onKeyDown={(event) => {
          // Enter sends, shift+enter is a new line — what a chat does. The
          // form's own submit still works, so nothing here is the only way.
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            say();
          }
        }}
      />
      <div className="flex justify-end">
        <SubmitButton
          label="Say it"
          pendingLabel="gary is answering…"
          pending={busy}
          disabled={disabled}
          data-testid="say"
        />
      </div>
    </form>
  );
}
