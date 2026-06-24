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

// ── Chart view — diverging bar ────────────────────────────────────────────────

function HorizonChart({ preds }: { preds: Record<number, MLHorizonPrediction> }) {
  const W = 280, H = 96;
  const PAD = { top: 8, right: 52, bottom: 22, left: 40 };
  const innerW = W - PAD.left - PAD.right;
  const BAR_H = 16, BAR_GAP = 8;
  const centerX = PAD.left + innerW / 2;

  const dim  = "var(--text-dim)";
  const brd  = "var(--border)";
  const surf = "var(--surface2)";

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="horizon-chart-svg">
      <text x={PAD.left}      y={H - 5} textAnchor="middle" fontSize={8} style={{ fill: dim }}>BEAR</text>
      <text x={centerX}       y={H - 5} textAnchor="middle" fontSize={8} style={{ fill: dim }}>50%</text>
      <text x={W - PAD.right} y={H - 5} textAnchor="middle" fontSize={8} style={{ fill: dim }}>BULL</text>

      <line x1={centerX} y1={PAD.top} x2={centerX} y2={H - 16}
        style={{ stroke: brd }} strokeWidth={1} strokeDasharray="3 2" />

      {HORIZONS.map((h, i) => {
        const p = preds[h];
        if (!p) return null;

        const prob      = p.prob_up;
        const isBull    = p.signal === "bullish";
        const isBear    = p.signal === "bearish";
        const col       = isBull ? "var(--green)" : isBear ? "var(--red)" : "#94a3b8";
        const pct       = Math.round(prob * 100);
        const y         = PAD.top + i * (BAR_H + BAR_GAP);
        const barW      = Math.abs(prob - 0.5) * innerW;
        const barX      = prob >= 0.5 ? centerX : centerX - barW;
        const lblX      = isBull ? barX + barW + 5 : barX - 5;
        const lblAnchor = isBull ? "start" : "end";

        return (
          <g key={h}>
            <rect x={PAD.left} y={y} width={innerW} height={BAR_H} style={{ fill: surf }} rx={2} />
            <rect x={barX} y={y} width={Math.max(barW, 1)} height={BAR_H}
              style={{ fill: col }} opacity={0.85} rx={2} />
            <text x={PAD.left - 5} y={y + BAR_H / 2 + 4}
              textAnchor="end" fontSize={9} style={{ fill: dim }}>{HORIZON_LABEL[h]}</text>
            <text x={lblX} y={y + BAR_H / 2 + 4}
              textAnchor={lblAnchor} fontSize={8.5} style={{ fill: col }} fontWeight={700}>{pct}%</text>
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
