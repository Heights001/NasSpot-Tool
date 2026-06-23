import { useEffect } from "react";
import type { TriggeredAlert } from "../hooks/useAlerts";

interface Props {
  toasts: TriggeredAlert[];
  onDismiss: (id: string) => void;
}

const AUTODISMISS_MS = 10_000;

export function ToastContainer({ toasts, onDismiss }: Props) {
  useEffect(() => {
    if (toasts.length === 0) return;
    const latest = toasts[toasts.length - 1];
    const timer = setTimeout(() => onDismiss(latest.id), AUTODISMISS_MS);
    return () => clearTimeout(timer);
  }, [toasts, onDismiss]);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className="toast">
          <span className="toast-icon">!</span>
          <span className="toast-body">
            <strong>{t.symbol}</strong>{" "}
            {t.type === "peg"
              ? `peg broken — ${t.current_price.toFixed(4)}`
              : `${t.direction === "above" ? ">" : "<"} ${t.threshold} hit — ${t.current_price}`}
          </span>
          <button className="toast-close" onClick={() => onDismiss(t.id)}>
            x
          </button>
        </div>
      ))}
    </div>
  );
}
