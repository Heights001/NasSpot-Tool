import type { IntelSnapshot } from "../types";

const LABEL: Record<string, string> = {
  lean_long: "LEAN LONG",
  lean_short: "LEAN SHORT",
  neutral: "NEUTRAL",
  suppressed: "SUPPRESSED",
};

const COLOR: Record<string, string> = {
  lean_long: "signal--long",
  lean_short: "signal--short",
  neutral: "signal--neutral",
  suppressed: "signal--suppressed",
};

interface Props {
  snap: IntelSnapshot;
}

export default function SignalBadge({ snap }: Props) {
  const composite = snap.ta_composite ?? "neutral";
  const cls = COLOR[composite] ?? "signal--neutral";
  const label = LABEL[composite] ?? composite.toUpperCase();

  return (
    <div className="signal-section">
      <div className={`signal-badge ${cls}`}>{label}</div>
      <div className="signal-details">
        {snap.rsi_14 != null && (
          <span className="signal-pill">
            RSI&nbsp;{Number(snap.rsi_14).toFixed(1)}
          </span>
        )}
        {snap.bb_pct_b != null && (
          <span className="signal-pill">
            BB%B&nbsp;{Number(snap.bb_pct_b).toFixed(2)}
          </span>
        )}
        {snap.sma_trend && (
          <span className={`signal-pill sma-${snap.sma_trend}`}>
            SMA&nbsp;{snap.sma_trend === "bullish" ? "↑" : "↓"}
          </span>
        )}
      </div>
      {snap.ta_reasoning && (
        <div className="signal-reasoning">{snap.ta_reasoning}</div>
      )}
    </div>
  );
}
