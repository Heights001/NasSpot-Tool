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

// ── Chart view — vertical bar chart ──────────────────────────────────────────

function HorizonChart({ preds }: { preds: Record<number, MLHorizonPrediction> }) {
  const W = 240, H = 100;
  const PAD = { top: 14, right: 12, bottom: 24, left: 32 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const BAR_W = 42, BAR_GAP = (innerW - BAR_W * HORIZONS.length) / (HORIZONS.length + 1);
  const neutralY = PAD.top + 0.5 * innerH;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="horizon-chart-svg">
      {/* Y-axis ticks */}
      {[0, 0.5, 1].map(t => {
        const y = PAD.top + (1 - t) * innerH;
        return (
          <g key={t}>
            <line x1={PAD.left} y1={y} x2={PAD.left + innerW} y2={y}
              stroke={t === 0.5 ? "#444" : "#252525"}
              strokeWidth={t === 0.5 ? 1 : 0.5}
              strokeDasharray={t === 0.5 ? "3 2" : undefined} />
            <text x={PAD.left - 4} y={y + 3.5} textAnchor="end" fontSize={7.5} fill="#555">
              {`${Math.round(t * 100)}%`}
            </text>
          </g>
        );
      })}

      {HORIZONS.map((h, i) => {
        const p = preds[h];
        if (!p) return null;

        const prob   = p.prob_up;
        const isBull = p.signal === "bullish";
        const isBear = p.signal === "bearish";
        const col    = isBull ? "#22c55e" : isBear ? "#ef4444" : "#94a3b8";
        const pct    = Math.round(prob * 100);

        const barX  = PAD.left + BAR_GAP * (i + 1) + BAR_W * i;
        const barH  = Math.abs(prob - 0.5) * innerH;
        const barY  = prob >= 0.5 ? neutralY - barH : neutralY;

        return (
          <g key={h}>
            {/* Bar background */}
            <rect x={barX} y={PAD.top} width={BAR_W} height={innerH}
              fill="#1a1a1a" rx={2} />
            {/* Value bar */}
            <rect x={barX} y={barY} width={BAR_W} height={Math.max(barH, 1)}
              fill={col} opacity={0.85} rx={2} />
            {/* Percentage label inside/above bar */}
            <text x={barX + BAR_W / 2} y={barY - 4} textAnchor="middle"
              fontSize={8} fill={col} fontWeight={700}>
              {pct}%
            </text>
            {/* X-axis label */}
            <text x={barX + BAR_W / 2} y={H - 6} textAnchor="middle"
              fontSize={8} fill="#555">
              {HORIZON_LABEL[h]}
            </text>
          </g>
        );
      })}
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
