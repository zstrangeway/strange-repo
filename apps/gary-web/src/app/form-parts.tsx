"use client";

export function Field({
  label,
  name,
  type = "text",
  autoComplete,
}: {
  label: string;
  name: string;
  type?: string;
  autoComplete?: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-black/60 dark:text-white/60">{label}</span>
      <input
        name={name}
        type={type}
        autoComplete={autoComplete}
        data-testid={`field-${name}`}
        className="rounded border border-black/15 bg-transparent px-3 py-2 text-base dark:border-white/20"
      />
    </label>
  );
}

export function Submit({ label, pending }: { label: string; pending: boolean }) {
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-50"
    >
      {pending ? "Working…" : label}
    </button>
  );
}

export function Notice({ error, confirmation }: { error?: string; confirmation?: string }) {
  if (error) {
    return (
      <p
        data-testid="error"
        role="alert"
        className="rounded bg-red-100 px-3 py-2 text-sm text-red-800 dark:bg-red-950 dark:text-red-300"
      >
        {error}
      </p>
    );
  }

  if (confirmation) {
    return (
      <p
        data-testid="confirmation"
        role="status"
        className="rounded bg-green-100 px-3 py-2 text-sm text-green-800 dark:bg-green-950 dark:text-green-300"
      >
        {confirmation}
      </p>
    );
  }

  return null;
}
