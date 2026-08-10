import { redirect } from "next/navigation";

import { Separator } from "@gary/ui/components/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@gary/ui/components/sidebar";

import { currentUser } from "@/lib/session";

import AppSidebar from "./app-sidebar";
import PageTitle from "./page-title";

// The session is read per request, so nothing under here can be prerendered.
export const dynamic = "force-dynamic";

export default async function AppLayout({
  children,
}: LayoutProps<"/">) {
  // The guard lives here rather than in each page: every route inside this
  // group is signed-in-only, and a page that forgets the check would be a
  // page that quietly leaks.
  const user = await currentUser();
  if (!user) {
    redirect("/login");
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
