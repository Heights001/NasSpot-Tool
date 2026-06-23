import type { MLInstrumentSignal } from "../types";

const HORIZONS = [15, 30, 60];
const HORIZON_LABEL: Record<number, string> = { 15: "+15m", 30: "+30m", 60: "+1hr" };

interface Props {
  signal: MLInstrumentSignal;
}

function ConfidenceDot({ level }: { level: string }) {
  const cls =
    level === "high" ? "conf-dot conf-dot--high"
    : level === "medium" ? "conf-dot conf-dot--med"
    : "conf-dot conf-dot--low";
  return <span className={cls} title={`Confidence: ${level}`} />;
}

export default function HorizonBar({ signal }: Props) {
  if (signal.is_peg) {
    return (
      <div className="horizon-section">
        <div className="horizon-header">ML DIRECTION</div>
        <div className="horizon-peg">STABLE — USDT PEG ANCHOR  $1.000</div>
      </div>
    );
  }

  const preds = signal.predictions;
  const hasData = Object.keys(preds).length > 0;

  if (!hasData) {
    return (
      <div className="horizon-section">
        <div className="horizon-header">ML DIRECTION</div>
        <div className="horizon-no-data">Training data loading…</div>
      </div>
    );
  }

  return (
    <div className="horizon-section">
      <div className="horizon-header">ML DIRECTION FORECAST</div>
      {HORIZONS.map((h) => {
        const p = preds[h];
        if (!p) return null;
        const pctUp = Math.round(p.prob_up * 100);
        const pctDown = 100 - pctUp;
        const isBull = p.signal === "bullish";
        const isBear = p.signal === "bearish";
        const barCls = isBull ? "hbar--bull" : isBear ? "hbar--bear" : "hbar--neutral";
        const signalLabel = p.signal.toUpperCase();

        return (
          <div key={h} className="horizon-row">
            <span className="horizon-label">{HORIZON_LABEL[h]}</span>
            <div className="horizon-track">
              {/* Center line at 50% */}
              <div className="horizon-center-line" />
              {/* Bar fills from 50% toward whichever direction is stronger */}
              {isBull ? (
                <div
                  className={`horizon-fill ${barCls}`}
                  style={{
                    left: "50%",
                    width: `${(pctUp - 50) * 2}%`,
                  }}
                />
              ) : isBear ? (
                <div
                  className={`horizon-fill ${barCls}`}
                  style={{
                    left: `${pctUp * 2}%`,
                    width: `${(pctDown - 50) * 2}%`,
                  }}
                />
              ) : (
                <div
                  className={`horizon-fill ${barCls}`}
                  style={{ left: "40%", width: "20%" }}
                />
              )}
            </div>
            <span className={`horizon-signal ${barCls}`}>{signalLabel}</span>
            <span className="horizon-pct">
              {isBull ? `${pctUp}%↑` : isBear ? `${pctDown}%↓` : "—"}
            </span>
            <ConfidenceDot level={p.confidence} />
          </div>
        );
      })}
      <div className="horizon-legend">
        <span className="conf-dot conf-dot--high" /> high &nbsp;
        <span className="conf-dot conf-dot--med" /> medium &nbsp;
        <span className="conf-dot conf-dot--low" /> low confidence
      </div>
    </div>
  );
}
