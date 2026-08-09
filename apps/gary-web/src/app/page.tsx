import ApiStatus from "./api-status";

// Read the API URL per request rather than baking it into the client bundle
// at build time, then hand it to the browser-side component as a prop.
export const dynamic = "force-dynamic";

export default function Home() {
  const baseUrl = process.env.GARY_API_URL ?? "http://127.0.0.1:8000";

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-3xl font-semibold tracking-tight">gary-web</h1>
      <p className="flex items-center gap-3 text-lg">
        <span className="text-black/60 dark:text-white/60">gary-api status:</span>
        <ApiStatus baseUrl={baseUrl} />
      </p>
    </main>
  );
}
