import { useCallback, useEffect, useState } from "react";
import type { AsyncState } from "../utils/dashboardStats";
import { publicError } from "../utils/publicText";

const LOAD_ERROR = "This information could not be loaded. Check that the MediAssist API is running, then try again.";
const LOADING = { status: "loading" } as const;

type Settled<T> = { load: () => Promise<T>; attempt: number; state: AsyncState<T> };

export function useAsync<T>(load: () => Promise<T>): { state: AsyncState<T>; reload: () => void } {
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    load().then(
      (data) => {
        if (!cancelled) setSettled({ load, attempt, state: { status: "ready", data } });
      },
      (error: unknown) => {
        if (cancelled) return;
        const message = typeof navigator !== "undefined" && !navigator.onLine ? "You appear to be offline." : publicError(error instanceof Error ? error.message : LOAD_ERROR, LOAD_ERROR);
        setSettled({ load, attempt, state: { status: "error", message } });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [load, attempt]);

  const reload = useCallback(() => setAttempt((value) => value + 1), []);
  // A result from a previous loader or attempt is stale: report loading instead of showing it.
  const current = settled && settled.load === load && settled.attempt === attempt ? settled.state : LOADING;
  return { state: current, reload };
}
