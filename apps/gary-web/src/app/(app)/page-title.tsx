"use client";

import { usePathname } from "next/navigation";

import { titleFor } from "./nav";

// Reads the title out of the same NAV the sidebar renders, so the header and
// the highlighted nav item can never disagree about where you are.
export default function PageTitle() {
  const title = titleFor(usePathname());

  return title ? <span className="text-sm font-medium">{title}</span> : null;
}
