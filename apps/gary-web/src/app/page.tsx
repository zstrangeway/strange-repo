export const dynamic = "force-dynamic";

const UNAVAILABLE = "unavailable";

// gary-api scales to zero, so the first request after an idle period arrives
// while Fly is still starting the machine. Retry across that window rather
// than reporting an outage.
const ATTEMPTS = 5;
const RETRY_DELAY_MS = 1_000;
const REQUEST_TIMEOUT_MS = 5_000;

async function fetchStatus(baseUrl: string): Promise<string | null> {
  const response = await fetch(`${baseUrl}/health`, {
    cache: "no-store",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  if (!response.ok) {
    throw new Error(`responded ${response.status}`);
  }

  const body = await response.json();
  return typeof body?.status === "string" ? body.status : null;
}

async function getApiStatus(): Promise<string> {
  const baseUrl = process.env.GARY_API_URL ?? "http://127.0.0.1:8000";

  for (let attempt = 1; attempt <= ATTEMPTS; attempt++) {
    try {
      const status = await fetchStatus(baseUrl);
      if (status !== null) {
        return status;
      }
      return UNAVAILABLE;
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

  return UNAVAILABLE;
}

export default async function Home() {
  const status = await getApiStatus();
  const healthy = status !== UNAVAILABLE;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-3xl font-semibold tracking-tight">gary-web</h1>
      <p className="flex items-center gap-3 text-lg">
        <span className="text-black/60 dark:text-white/60">gary-api status:</span>
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
      </p>
    </main>
  );
}
