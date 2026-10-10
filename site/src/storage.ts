import { useEffect, useState } from "react";
import type { Tracking } from "./types";

const KEY = "intern-tracker:v1";
const EMPTY: Tracking = { saved: {}, applied: {} };

function read(): Tracking {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return EMPTY;
    const parsed = JSON.parse(raw);
    return { saved: parsed.saved ?? {}, applied: parsed.applied ?? {} };
  } catch {
    return EMPTY;
  }
}

/** Saved/applied state, kept in this browser only. */
export function useTracking() {
  const [state, setState] = useState<Tracking>(read);
  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch {
      /* storage unavailable (private mode); state still works for this visit */
    }
  }, [state]);

  const toggle = (kind: keyof Tracking, id: string) =>
    setState((s) => {
      const next = { ...s[kind] };
      if (next[id]) delete next[id];
      else next[id] = new Date().toISOString().slice(0, 10);
      return { ...s, [kind]: next };
    });

  return { tracking: state, toggle };
}
