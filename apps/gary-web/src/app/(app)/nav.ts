import { House, UserRound } from "lucide-react";

// The signed-in routes, in one place: the sidebar renders it and the header
// reads the current page's title out of it. Two routes is all gary has —
// this list grows when a route does, not before.
export const NAV = [
  { title: "Home", url: "/", icon: House },
  { title: "Profile", url: "/profile", icon: UserRound },
] as const;

export function titleFor(pathname: string) {
  return NAV.find((item) => item.url === pathname)?.title;
}
