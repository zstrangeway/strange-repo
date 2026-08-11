"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Separator } from "@gary/ui/components/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@gary/ui/components/sidebar";

import { SessionProvider, useSession } from "@/lib/use-session";

import AppSidebar from "./app-sidebar";
import PageTitle from "./page-title";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <SessionProvider>
      <Guarded>{children}</Guarded>
    </SessionProvider>
  );
}

// The guard lives here rather than in each page: every route inside this
// group is signed-in-only, and a page that forgets the check would be a page
// that quietly leaks.
function Guarded({ children }: { children: ReactNode }) {
  const { user, loading } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  // Nothing at all until gary-api has answered. Rendering the frame first
  // would show a sidebar with nobody in it, then snatch it away.
  if (!user) {
    return null;
  }

  return (
    <SidebarProvider>
      <AppSidebar name={user.display_name} email={user.email} />
      <SidebarInset>
        <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <PageTitle />
        </header>
        {/* One measure for every page in the group, so a page never has to
            reinvent its own width and drift from the others. */}
        <div className="flex w-full max-w-2xl flex-1 flex-col gap-6 p-6">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
