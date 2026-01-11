import { Outlet } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { NoteList } from "@/features/notes/NoteList";
import { UserMenu } from "@/components/UserMenu";
import { useUI } from "@/stores/ui";

// Two-pane notes shell (D-01/D-02/D-03, PLAT-04): collapsible sidebar (note list + user menu) wired to the shared UI store, Sheet drawer ≤sm, routed editor pane on the right.
export function AppShell() {
  const collapsed = useUI((s) => s.sidebarCollapsed);
  const setCollapsed = useUI((s) => s.setSidebarCollapsed);

  return (
    <SidebarProvider
      open={!collapsed}
      onOpenChange={(open) => setCollapsed(!open)}
      style={
        {
          "--sidebar-width": "280px",
        } as React.CSSProperties
      }
    >
      <Sidebar collapsible="offcanvas">
        <SidebarContent>
          <NoteList />
        </SidebarContent>
        <SidebarFooter>
          <UserMenu />
        </SidebarFooter>
      </Sidebar>

      <SidebarInset>
        <header className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
          <SidebarTrigger aria-label="Toggle sidebar" />
        </header>
        <main className="flex flex-1 flex-col overflow-hidden">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
