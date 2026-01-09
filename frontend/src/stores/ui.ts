import { create } from "zustand";

/**
 * UI store — client-only view state for the notes shell.
 *
 * - sidebarCollapsed: desktop sidebar collapse toggle (UI-SPEC D-02).
 * - mobileDrawerOpen: phone slide-over drawer behind the hamburger (UI-SPEC D-03).
 *
 * Server state lives in TanStack Query, never here.
 */
interface UIState {
  sidebarCollapsed: boolean;
  mobileDrawerOpen: boolean;
  toggleCollapsed: () => void;
  /** Set the desktop collapse state directly (controlled shadcn SidebarProvider). */
  setSidebarCollapsed: (collapsed: boolean) => void;
  setMobileDrawer: (open: boolean) => void;
}

export const useUI = create<UIState>((set) => ({
  sidebarCollapsed: false,
  mobileDrawerOpen: false,
  toggleCollapsed: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
  setMobileDrawer: (mobileDrawerOpen) => set({ mobileDrawerOpen }),
}));
