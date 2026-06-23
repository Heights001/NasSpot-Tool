import { useState } from "react";
import type { SpotPrice } from "../types";

interface Props {
  fxPrices: SpotPrice[];
  onClose: () => void;
}

export function QuickConvert({ fxPrices, onClose }: Props) {
  const [selectedSymbol, setSelectedSymbol] = useState(
    fxPrices[0]?.symbol ?? ""
  );
  const [amount, setAmount] = useState("1000");
  const [direction, setDirection] = useState<"forward" | "reverse">("forward");

  const inst = fxPrices.find((f) => f.symbol === selectedSymbol);
  const rate = inst?.price ? parseFloat(inst.price) : null;
  const precision = inst?.display_precision ?? 4;

  const [base, quote] = selectedSymbol.split("/");
  const fromCcy = direction === "forward" ? base : quote;
  const toCcy = direction === "forward" ? quote : base;

  const amt = parseFloat(amount) || 0;
  const result =
    rate != null && amt > 0
      ? direction === "forward"
        ? amt * rate
        : amt / rate
      : null;

  const rateStr =
    rate != null
      ? rate.toLocaleString("en-US", {
          minimumFractionDigits: precision,
          maximumFractionDigits: precision,
        })
      : "—";

  const resultStr =
    result != null
      ? result.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : "—";

  return (
    <div className="side-panel">
      <div className="side-panel-header">
        <span>Quick Convert</span>
        <button className="panel-close" onClick={onClose}>
          x
        </button>
      </div>

      <div className="qc-body">
        <select
          value={selectedSymbol}
          onChange={(e) => {
            setSelectedSymbol(e.target.value);
            setDirection("forward");
          }}
        >
          {fxPrices.map((f) => (
            <option key={f.symbol} value={f.symbol}>
              {f.symbol}
            </option>
          ))}
        </select>

        <div className="qc-rate">
          1 {base} = {rateStr} {quote}
        </div>

        <div className="qc-inputs">
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            min="0"
            step="any"
          />
          <span className="qc-ccy">{fromCcy}</span>
          <button
            className="qc-flip"
            onClick={() =>
              setDirection((d) => (d === "forward" ? "reverse" : "forward"))
            }
            title="Flip direction"
          >
            ⇄
          </button>
          <span className="qc-result">{resultStr}</span>
          <span className="qc-ccy">{toCcy}</span>
        </div>
      </div>
    </div>
  );
}
