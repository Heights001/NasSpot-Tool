import { useState, useCallback } from "react";

const KEY = "nasspot_watchlist";

function loadStarred(): Set<number> {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return new Set();
    return new Set(JSON.parse(raw) as number[]);
  } catch {
    return new Set();
  }
}

export function useWatchlist() {
  const [starred, setStarred] = useState<Set<number>>(loadStarred);

  const toggle = useCallback((id: number) => {
    setStarred((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      localStorage.setItem(KEY, JSON.stringify([...next]));
      return next;
    });
  }, []);

  return { starred, toggle };
}
