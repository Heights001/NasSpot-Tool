import { useState } from "react";
import type { MLInstrumentSignal, MLHorizonPrediction } from "../types";

const HORIZONS = [15, 30, 60];
const HORIZON_LABEL: Record<number, string> = { 15: "+15m", 30: "+30m", 60: "+1hr" };

interface Props {
  signal: MLInstrumentSignal;
}

function ConfidenceDot({ level }: { level: string }) {
  const cls =
    level === "high"   ? "conf-dot conf-dot--high"
    : level === "medium" ? "conf-dot conf-dot--med"
    : "conf-dot conf-dot--low";
  return <span className={cls} title={`Confidence: ${level}`} />;
}

// ── Chart view — semicircle gauges ───────────────────────────────────────────

function HorizonChart({ preds }: { preds: Record<number, MLHorizonPrediction> }) {
  const W = 280, H = 92;
  const R = 36, CY = 60;
  const CXS = [50, 140, 230];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="horizon-chart-svg">
      {HORIZONS.map((h, i) => {
        const p = preds[h];
        if (!p) return null;

        const prob = Math.min(Math.max(p.prob_up, 0.01), 0.99);
        const cx   = CXS[i];
        const col  = p.signal === "bullish" ? "var(--green)"
                   : p.signal === "bearish" ? "var(--red)"
                   : "#94a3b8";
        const pct  = Math.round(p.prob_up * 100);

        // Needle angle: θ=π at prob=0 (left), θ=0 at prob=1 (right)
        const theta = Math.PI * (1 - prob);
        const nx = cx + R * Math.cos(theta);
        const ny = CY - R * Math.sin(theta);

        // Full track arc (upper semicircle, sweep=0 = counterclockwise in screen space = upper)
        const track = `M ${cx - R} ${CY} A ${R} ${R} 0 0 0 ${cx + R} ${CY}`;
        // Fill arc from bearish end to needle (always ≤ 180°, large-arc=0)
        const fill  = `M ${cx - R} ${CY} A ${R} ${R} 0 0 0 ${nx.toFixed(2)} ${ny.toFixed(2)}`;

        return (
          <g key={h}>
            {/* Track */}
            <path d={track} fill="none" style={{ stroke: "var(--surface2)" }}
              strokeWidth={7} strokeLinecap="round" />
            {/* Coloured fill */}
            <path d={fill} fill="none" style={{ stroke: col }}
              strokeWidth={7} strokeLinecap="round" opacity={0.9} />
            {/* 50% tick at top */}
            <line x1={cx} y1={CY - R - 2} x2={cx} y2={CY - R + 5}
              style={{ stroke: "var(--border)" }} strokeWidth={1.5} />
            {/* Needle */}
            <line x1={cx} y1={CY} x2={nx.toFixed(2)} y2={ny.toFixed(2)}
              style={{ stroke: "var(--text)" }} strokeWidth={1.5} strokeLinecap="round" />
            {/* Pivot */}
            <circle cx={cx} cy={CY} r={3.5} style={{ fill: col }} />
            {/* % label */}
            <text x={cx} y={CY + 15} textAnchor="middle" fontSize={10}
              style={{ fill: col }} fontWeight={700}>{pct}%</text>
            {/* Horizon label */}
            <text x={cx} y={CY + 27} textAnchor="middle" fontSize={8.5}
              style={{ fill: "var(--text-dim)" }}>{HORIZON_LABEL[h]}</text>
          </g>
        );
      })}
      {/* Axis hints */}
      <text x={4}     y={CY + 4} textAnchor="start" fontSize={7} style={{ fill: "var(--text-dim)" }}>BEAR</text>
      <text x={W - 4} y={CY + 4} textAnchor="end"   fontSize={7} style={{ fill: "var(--text-dim)" }}>BULL</text>
    </svg>
  );
}

// ── Bar view (existing) ───────────────────────────────────────────────────────

function HorizonBars({ preds }: { preds: Record<number, MLHorizonPrediction> }) {
  return (
    <>
      {HORIZONS.map((h) => {
        const p = preds[h];
        if (!p) return null;
        const pctUp   = Math.round(p.prob_up * 100);
        const pctDown = 100 - pctUp;
        const isBull  = p.signal === "bullish";
        const isBear  = p.signal === "bearish";
        const barCls  = isBull ? "hbar--bull" : isBear ? "hbar--bear" : "hbar--neutral";

        return (
          <div key={h} className="horizon-row">
            <span className="horizon-label">{HORIZON_LABEL[h]}</span>
            <div className="horizon-track">
              <div className="horizon-center-line" />
              {isBull ? (
                <div className={`horizon-fill ${barCls}`}
                  style={{ left: "50%", width: `${(pctUp - 50) * 2}%` }} />
              ) : isBear ? (
                <div className={`horizon-fill ${barCls}`}
                  style={{ left: `${pctUp * 2}%`, width: `${(pctDown - 50) * 2}%` }} />
              ) : (
                <div className={`horizon-fill ${barCls}`}
                  style={{ left: "40%", width: "20%" }} />
              )}
            </div>
            <span className={`horizon-signal ${barCls}`}>{p.signal.toUpperCase()}</span>
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
    </>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function HorizonBar({ signal }: Props) {
  const [chartMode, setChartMode] = useState(false);

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
      <div className="horizon-header">
        ML DIRECTION FORECAST
        <button
          className={`horizon-view-toggle${chartMode ? " horizon-view-toggle--active" : ""}`}
          onClick={() => setChartMode(v => !v)}
          title={chartMode ? "Switch to bars" : "Switch to chart"}
        >
          {chartMode ? "≡" : "⌁"}
        </button>
      </div>

      {chartMode
        ? <HorizonChart preds={preds} />
        : <HorizonBars  preds={preds} />
      }
    </div>
  );
}
