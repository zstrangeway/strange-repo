"use client";

import { useEffect, useState } from "react";

const UNAVAILABLE = "unavailable";
const ATTEMPTS = 5;
const RETRY_DELAY_MS = 1_000;

export default function ApiStatus({ baseUrl }: { baseUrl: string }) {
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      // gary-api scales to zero, so the first request may arrive while Fly is
      // still starting the machine. Retry across that window.
      for (let attempt = 1; attempt <= ATTEMPTS; attempt++) {
        try {
          const response = await fetch(`${baseUrl}/health`, {
            cache: "no-store",
          });
          if (!response.ok) {
            throw new Error(`responded ${response.status}`);
          }

          const body = await response.json();
          if (typeof body?.status !== "string") {
            throw new Error("unexpected body");
          }

          if (!cancelled) {
            setStatus(body.status);
          }
          return;
        } catch (error) {
          console.error(
            `gary-api unreachable at ${baseUrl} (attempt ${attempt}/${ATTEMPTS}):`,
            error,
          );
          if (attempt < ATTEMPTS) {
            await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
          }
        }
      }

      if (!cancelled) {
        setStatus(UNAVAILABLE);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [baseUrl]);

  if (status === null) {
    return (
      <span
        data-testid="api-status"
        className="rounded-full bg-black/5 px-3 py-1 font-mono text-black/50 dark:bg-white/10 dark:text-white/50"
      >
        checking…
      </span>
    );
  }

  const healthy = status !== UNAVAILABLE;

  return (
    <span
      data-testid="api-status"
      className={
        healthy
          ? "rounded-full bg-green-100 px-3 py-1 font-mono text-green-800 dark:bg-green-950 dark:text-green-300"
          : "rounded-full bg-red-100 px-3 py-1 font-mono text-red-800 dark:bg-red-950 dark:text-red-300"
      }
    >
      {status}
    </span>
  );
}
