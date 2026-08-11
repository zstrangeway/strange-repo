import { Swords, UserRound } from "lucide-react";

// The signed-in routes, in one place: the sidebar renders it and the header
// reads the current page's title out of it. This list grows when a route
// does, not before.
//
// Campaigns is "/" rather than "/campaigns" because it is where signing in
// lands you. There is no separate home — a list of your games proves the
// session works just as well as a greeting did, and is also the thing you
// came for.
export const NAV = [
  { title: "Campaigns", url: "/", icon: Swords },
  { title: "Profile", url: "/profile", icon: UserRound },
] as const;

export function titleFor(pathname: string) {
  const exact = NAV.find((item) => item.url === pathname)?.title;
  if (exact) {
    return exact;
  }

  // The pages under a campaign are not nav items — there is one per campaign
  // and they are reached from the list, not from the sidebar. They still
  // want a header, so they get the section's name rather than nothing.
  if (pathname.startsWith("/campaigns")) {
    return "Campaigns";
  }

  return undefined;
}

/** Which nav item to light up. A campaign page belongs to Campaigns even
 *  though its URL is not the one in the list. */
export function activeFor(pathname: string, url: string) {
  if (url === "/") {
    return pathname === "/" || pathname.startsWith("/campaigns");
  }
  return pathname === url;
}
