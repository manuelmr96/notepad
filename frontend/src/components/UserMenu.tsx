import { ChevronsUpDown, LogOut, MonitorOff } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useAuth } from "@/stores/auth";
import { useLogout, useLogoutAll } from "@/features/auth/useAuthMutations";

// Sidebar-footer user menu (D-04, AUTH-04): shows the signed-in identity (falls back to "Account" when email is absent after a boot refresh) and a Log out action.
export function UserMenu() {
  const email = useAuth((s) => s.email);
  const logout = useLogout();
  const logoutAll = useLogoutAll();
  const identity = email ?? "Account";

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              aria-label="User menu"
              className="data-[state=open]:bg-sidebar-accent"
            >
              <span className="flex aria-hidden:true size-8 shrink-0 items-center justify-center rounded-md bg-sidebar-accent text-sm font-semibold uppercase">
                {identity.charAt(0)}
              </span>
              <span className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">{identity}</span>
              </span>
              <ChevronsUpDown className="ml-auto size-4" aria-hidden="true" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            side="top"
            align="start"
            className="w-(--radix-dropdown-menu-trigger-width) min-w-56"
          >
            <DropdownMenuLabel className="truncate font-normal text-muted-foreground">
              {identity}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => logout.mutate()}
              disabled={logout.isPending}
            >
              <LogOut aria-hidden="true" />
              Log out
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => logoutAll.mutate()}
              disabled={logoutAll.isPending}
            >
              <MonitorOff aria-hidden="true" />
              Log out all sessions
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
