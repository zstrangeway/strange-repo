"use client";

import { useSession } from "@/lib/use-session";

export default function Home() {
  // The layout renders nothing until there is a user, so by the time this
  // runs there is one. The check is for the type, not for the case.
  const { user } = useSession();
  if (!user) {
    return null;
  }

  return (
    <h1 data-testid="welcome" className="text-3xl font-semibold tracking-tight">
      Welcome Home, {user.display_name}
    </h1>
  );
}
