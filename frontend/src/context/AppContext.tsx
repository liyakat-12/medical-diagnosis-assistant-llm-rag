import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

interface Toast {
  id: number;
  message: string;
}

export const SIDEBAR_MIN = 240;
export const SIDEBAR_MAX = 380;
export const SIDEBAR_DEFAULT = 280;
export const SIDEBAR_RAIL = 72;

function readStoredNumber(key: string, fallback: number, min: number, max: number): number {
  try {
    const raw = window.localStorage.getItem(key);
    const value = Number(raw);
    if (!Number.isFinite(value)) return fallback;
    return Math.min(max, Math.max(min, value));
  } catch {
    return fallback;
  }
}

function readStoredFlag(key: string, fallback: boolean): boolean {
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === "1") return true;
    if (raw === "0") return false;
    return fallback;
  } catch {
    return fallback;
  }
}

interface AppContextValue {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  sidebarWidth: number;
  setSidebarWidth: (width: number) => void;
  toast: (message: string) => void;
  toasts: Toast[];
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setCollapsedState] = useState(() => readStoredFlag("mediassist.sidebarCollapsed", false));
  const [sidebarWidth, setWidthState] = useState(() => readStoredNumber("mediassist.sidebarWidth", SIDEBAR_DEFAULT, SIDEBAR_MIN, SIDEBAR_MAX));
  const [toasts, setToasts] = useState<Toast[]>([]);

  const setSidebarCollapsed = useCallback((collapsed: boolean) => {
    setCollapsedState(collapsed);
    try {
      window.localStorage.setItem("mediassist.sidebarCollapsed", collapsed ? "1" : "0");
    } catch {
      /* ignore quota */
    }
  }, []);

  const setSidebarWidth = useCallback((width: number) => {
    const next = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, Math.round(width)));
    setWidthState(next);
    try {
      window.localStorage.setItem("mediassist.sidebarWidth", String(next));
    } catch {
      /* ignore quota */
    }
  }, []);

  const toast = useCallback((message: string) => {
    const id = Date.now();
    setToasts((current) => [...current, { id, message }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id));
    }, 3200);
  }, []);

  const value = useMemo(
    () => ({
      sidebarOpen,
      setSidebarOpen,
      sidebarCollapsed,
      setSidebarCollapsed,
      sidebarWidth,
      setSidebarWidth,
      toast,
      toasts,
    }),
    [sidebarOpen, sidebarCollapsed, setSidebarCollapsed, sidebarWidth, setSidebarWidth, toast, toasts],
  );

  return (
    <AppContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((item) => (
          <div
            key={item.id}
            className="pointer-events-auto rounded-2xl border border-teal-100 bg-white px-4 py-3 text-sm font-semibold text-slate-800 shadow-lg"
            role="status"
          >
            {item.message}
          </div>
        ))}
      </div>
    </AppContext.Provider>
  );
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
