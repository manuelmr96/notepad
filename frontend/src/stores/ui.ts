import { create } from "zustand";

// UI store — client-only view state for the notes shell: sidebarCollapsed (desktop toggle, D-02) and mobileDrawerOpen (phone drawer, D-03). Server state lives in TanStack Query, never here.
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
