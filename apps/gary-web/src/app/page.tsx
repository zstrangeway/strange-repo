export const dynamic = "force-dynamic";

const UNAVAILABLE = "unavailable";

async function getApiStatus(): Promise<string> {
  const baseUrl = process.env.GARY_API_URL ?? "http://127.0.0.1:8000";

  try {
    const response = await fetch(`${baseUrl}/health`, { cache: "no-store" });
    if (!response.ok) {
      return UNAVAILABLE;
    }

    const body = await response.json();
    return typeof body?.status === "string" ? body.status : UNAVAILABLE;
  } catch (error) {
    // The page degrades to "unavailable" either way, but without this the
    // reason never surfaces anywhere.
    console.error(`gary-api unreachable at ${baseUrl}:`, error);
    return UNAVAILABLE;
  }
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
