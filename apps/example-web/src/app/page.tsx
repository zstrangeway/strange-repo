import { greet } from "@/lib/greeting";

export default function Home() {
  return (
    <main>
      <h1>{greet()}</h1>
      <p>example-web is running.</p>
    </main>
  );
}
