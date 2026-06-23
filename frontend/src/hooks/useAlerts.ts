import { useState, useCallback, useEffect, useRef } from "react";
import type { SpotBoardResponse } from "../types";

const STORAGE_KEY = "nasspot_alerts";

export interface Alert {
  id: string;
  instrument_id: number;
  symbol: string;
  type: "threshold" | "peg";
  threshold?: number;
  direction?: "above" | "below";
  created_at: string;
}

export interface TriggeredAlert extends Alert {
  current_price: number;
}

function load(): Alert[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Alert[]) : [];
  } catch {
    return [];
  }
}

function save(alerts: Alert[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(alerts));
}

export function useAlerts(boardData?: SpotBoardResponse) {
  const [alerts, setAlerts] = useState<Alert[]>(load);
  const [triggered, setTriggered] = useState<TriggeredAlert[]>([]);
  const firedRef = useRef<Set<string>>(new Set());

  const addAlert = useCallback((alert: Omit<Alert, "id" | "created_at">) => {
    const full: Alert = {
      ...alert,
      id: crypto.randomUUID(),
      created_at: new Date().toISOString(),
    };
    setAlerts((prev) => {
      const next = [...prev, full];
      save(next);
      return next;
    });
  }, []);

  const removeAlert = useCallback((id: string) => {
    firedRef.current.delete(id);
    setAlerts((prev) => {
      const next = prev.filter((a) => a.id !== id);
      save(next);
      return next;
    });
    setTriggered((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const dismissTriggered = useCallback((id: string) => {
    setTriggered((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    if (!boardData || alerts.length === 0) return;

    const allPrices = [...boardData.fx, ...boardData.crypto];
    const priceById: Record<number, number> = {};
    for (const sp of allPrices) {
      if (sp.price != null) {
        priceById[sp.instrument_id] = parseFloat(sp.price);
      }
    }

    const newTriggered: TriggeredAlert[] = [];
    for (const alert of alerts) {
      if (firedRef.current.has(alert.id)) continue;
      const price = priceById[alert.instrument_id];
      if (price == null) continue;

      let fires = false;
      if (alert.type === "peg") {
        fires = Math.abs(price - 1.0) > 0.005;
      } else if (alert.type === "threshold" && alert.threshold != null) {
        fires =
          alert.direction === "above"
            ? price >= alert.threshold
            : price <= alert.threshold;
      }

      if (fires) {
        firedRef.current.add(alert.id);
        newTriggered.push({ ...alert, current_price: price });
      }
    }

    if (newTriggered.length > 0) {
      setTriggered((prev) => [...prev, ...newTriggered]);
    }
  }, [boardData, alerts]);

  return { alerts, triggered, addAlert, removeAlert, dismissTriggered };
}
