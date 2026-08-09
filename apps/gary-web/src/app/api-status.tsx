"use client";

import { useEffect, useState } from "react";

const UNAVAILABLE = "unavailable";
const ATTEMPTS = 5;
const RETRY_DELAY_MS = 1_000;

type Health = { status: string; database: string };

function Pill({ testId, value }: { testId: string; value: string | null }) {
  if (value === null) {
    return (
      <span
        data-testid={testId}
        className="rounded-full bg-black/5 px-3 py-1 font-mono text-black/50 dark:bg-white/10 dark:text-white/50"
      >
        checking…
      </span>
    );
  }

  const healthy = value === "ok";

  return (
    <span
      data-testid={testId}
      className={
        healthy
          ? "rounded-full bg-green-100 px-3 py-1 font-mono text-green-800 dark:bg-green-950 dark:text-green-300"
          : "rounded-full bg-red-100 px-3 py-1 font-mono text-red-800 dark:bg-red-950 dark:text-red-300"
      }
    >
      {value}
    </span>
  );
}

export default function HealthStatus({ baseUrl }: { baseUrl: string }) {
  const [health, setHealth] = useState<Health | null>(null);

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
            setHealth({
              status: body.status,
              // Tolerate an older gary-api that does not report a database.
              database:
                typeof body?.database === "string" ? body.database : UNAVAILABLE,
            });
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
        // Nothing was reached, so nothing behind it can be reported on either.
        setHealth({ status: UNAVAILABLE, database: UNAVAILABLE });
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [baseUrl]);

  return (
    <dl className="grid grid-cols-[auto_auto] items-center gap-x-3 gap-y-3 text-lg">
      <dt className="text-black/60 dark:text-white/60">gary-api</dt>
      <dd>
        <Pill testId="api-status" value={health?.status ?? null} />
      </dd>
      <dt className="text-black/60 dark:text-white/60">database</dt>
      <dd>
        <Pill testId="database-status" value={health?.database ?? null} />
      </dd>
    </dl>
  );
}
