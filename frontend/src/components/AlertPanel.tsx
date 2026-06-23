import { useState } from "react";
import type { Alert } from "../hooks/useAlerts";
import type { SpotPrice } from "../types";

interface Props {
  alerts: Alert[];
  allInstruments: SpotPrice[];
  preselect?: number;
  onAdd: (alert: Omit<Alert, "id" | "created_at">) => void;
  onRemove: (id: string) => void;
  onClose: () => void;
}

export function AlertPanel({
  alerts,
  allInstruments,
  preselect,
  onAdd,
  onRemove,
  onClose,
}: Props) {
  const [formInstId, setFormInstId] = useState<number>(
    preselect ?? allInstruments[0]?.instrument_id ?? 0
  );
  const [formType, setFormType] = useState<"threshold" | "peg">("threshold");
  const [formThreshold, setFormThreshold] = useState("");
  const [formDirection, setFormDirection] = useState<"above" | "below">("above");

  const selectedInst = allInstruments.find((i) => i.instrument_id === formInstId);

  function handleInstChange(id: number) {
    setFormInstId(id);
    const inst = allInstruments.find((i) => i.instrument_id === id);
    if (formType === "peg" && !inst?.is_peg_watch) {
      setFormType("threshold");
    }
  }

  function handleAdd() {
    if (!selectedInst) return;
    if (formType === "threshold") {
      const t = parseFloat(formThreshold);
      if (!formThreshold || isNaN(t)) return;
      onAdd({
        instrument_id: formInstId,
        symbol: selectedInst.symbol,
        type: "threshold",
        threshold: t,
        direction: formDirection,
      });
      setFormThreshold("");
    } else {
      onAdd({
        instrument_id: formInstId,
        symbol: selectedInst.symbol,
        type: "peg",
      });
    }
  }

  return (
    <div className="side-panel">
      <div className="side-panel-header">
        <span>Alerts</span>
        <button className="panel-close" onClick={onClose}>
          x
        </button>
      </div>

      <div className="alert-form">
        <select
          value={formInstId}
          onChange={(e) => handleInstChange(Number(e.target.value))}
        >
          {allInstruments.map((inst) => (
            <option key={inst.instrument_id} value={inst.instrument_id}>
              {inst.symbol}
            </option>
          ))}
        </select>

        <select
          value={formType}
          onChange={(e) => setFormType(e.target.value as "threshold" | "peg")}
        >
          <option value="threshold">Price threshold</option>
          {selectedInst?.is_peg_watch && (
            <option value="peg">Peg broken (&gt; 0.5%)</option>
          )}
        </select>

        {formType === "threshold" && (
          <div className="alert-threshold-row">
            <select
              value={formDirection}
              onChange={(e) =>
                setFormDirection(e.target.value as "above" | "below")
              }
            >
              <option value="above">above</option>
              <option value="below">below</option>
            </select>
            <input
              type="number"
              value={formThreshold}
              onChange={(e) => setFormThreshold(e.target.value)}
              placeholder="Price"
              step="any"
            />
          </div>
        )}

        <button className="btn-primary" onClick={handleAdd}>
          Add alert
        </button>
      </div>

      <div className="alert-list">
        {alerts.length === 0 ? (
          <div className="panel-empty">No alerts set</div>
        ) : (
          alerts.map((alert) => (
            <div key={alert.id} className="alert-item">
              <span className="alert-desc">
                <strong>{alert.symbol}</strong>{" "}
                {alert.type === "peg"
                  ? "peg break"
                  : `${alert.direction === "above" ? ">" : "<"} ${alert.threshold}`}
              </span>
              <button
                className="alert-delete"
                onClick={() => onRemove(alert.id)}
              >
                x
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
