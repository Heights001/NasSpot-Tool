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

// ── Chart view ────────────────────────────────────────────────────────────────

function HorizonChart({ preds }: { preds: Record<number, MLHorizonPrediction> }) {
  const W = 280, H = 110;
  const PAD = { top: 14, right: 16, bottom: 28, left: 36 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const points = HORIZONS.map((h, i) => {
    const p = preds[h];
    const prob = p ? p.prob_up : 0.5;
    const x = PAD.left + (i / (HORIZONS.length - 1)) * innerW;
    const y = PAD.top + (1 - prob) * innerH;
    return { x, y, prob, h, p };
  }).filter(pt => pt.p);

  if (points.length < 2) return null;

  const neutralY = PAD.top + 0.5 * innerH;

  // Build filled area path between line and neutral (50%)
  const linePoints = points.map(pt => `${pt.x},${pt.y}`).join(" ");
  const areaPath =
    `M ${points[0].x},${neutralY} ` +
    points.map(pt => `L ${pt.x},${pt.y}`).join(" ") +
    ` L ${points[points.length - 1].x},${neutralY} Z`;

  // Determine dominant direction for fill colour
  const avgProb = points.reduce((s, p) => s + p.prob, 0) / points.length;
  const fillCol  = avgProb > 0.52 ? "rgba(34,197,94,0.18)" : avgProb < 0.48 ? "rgba(239,68,68,0.18)" : "rgba(148,163,184,0.12)";
  const lineCol  = avgProb > 0.52 ? "#22c55e" : avgProb < 0.48 ? "#ef4444" : "#94a3b8";

  // Y-axis ticks: 0%, 50%, 100%
  const yTicks = [0, 0.5, 1];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="horizon-chart-svg">
      {/* Y-axis grid lines + labels */}
      {yTicks.map(t => {
        const y = PAD.top + (1 - t) * innerH;
        return (
          <g key={t}>
            <line x1={PAD.left} y1={y} x2={PAD.left + innerW} y2={y}
              stroke={t === 0.5 ? "#444" : "#2a2a2a"} strokeWidth={t === 0.5 ? 1 : 0.5} strokeDasharray={t === 0.5 ? "3 3" : undefined} />
            <text x={PAD.left - 5} y={y + 3.5} textAnchor="end"
              fontSize={8} fill="#555">{`${Math.round(t * 100)}%`}</text>
          </g>
        );
      })}

      {/* Filled area */}
      <path d={areaPath} fill={fillCol} />

      {/* Line */}
      <polyline points={linePoints} fill="none" stroke={lineCol} strokeWidth={1.5} strokeLinejoin="round" />

      {/* Data points + x labels */}
      {points.map((pt) => {
        const isBull = pt.p && pt.p.signal === "bullish";
        const isBear = pt.p && pt.p.signal === "bearish";
        const dotCol = isBull ? "#22c55e" : isBear ? "#ef4444" : "#94a3b8";
        const pct = Math.round(pt.prob * 100);
        const labelY = pt.y > neutralY ? pt.y - 6 : pt.y + 12;
        return (
          <g key={pt.h}>
            <circle cx={pt.x} cy={pt.y} r={3.5} fill={dotCol} />
            <text x={pt.x} y={labelY} textAnchor="middle" fontSize={8} fill={dotCol} fontWeight={600}>
              {pct}%
            </text>
            <text x={pt.x} y={H - 6} textAnchor="middle" fontSize={8} fill="#555">
              {HORIZON_LABEL[pt.h]}
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
