import { redirect } from "next/navigation";

import { currentUser } from "@/lib/session";

import UnverifiedNotice from "./unverified-notice";

export default async function Home() {
  // Guarded here as well as in the layout, not for belt and braces: Next
  // renders a layout and its page concurrently, so this runs whether or not
  // the layout has decided to redirect. currentUser is request-cached, so
  // asking twice costs one call to gary-api.
  const user = await currentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <>
      <h1
        data-testid="welcome"
        className="text-3xl font-semibold tracking-tight"
      >
        Welcome Home, {user.display_name}
      </h1>

      {user.email_verified ? null : <UnverifiedNotice />}
    </>
  );
}
