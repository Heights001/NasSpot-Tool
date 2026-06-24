import { useState } from "react";
import type { VolumeInstrumentForecast } from "../types";

const HORIZONS: Array<"15" | "30" | "60"> = ["15", "30", "60"];
const HORIZON_LABEL: Record<string, string> = { "15": "15m", "30": "30m", "60": "1hr" };

function fmtVol(v: number): string {
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return v.toFixed(2);
}

const ACTIVITY_COL: Record<string, string> = {
  busy:    "var(--green)",
  typical: "var(--blue)",
  quiet:   "var(--text-dim)",
};

interface Props {
  data: VolumeInstrumentForecast;
}

// ── SVG chart view ────────────────────────────────────────────────────────────

function VolChart({ vals, maxVal }: { vals: number[]; maxVal: number }) {
  const W = 240, H = 80;
  const PAD = { top: 18, right: 12, bottom: 22, left: 8 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const count  = vals.length;
  const BAR_W  = Math.floor(innerW / count) - 6;
  const GAP    = (innerW - BAR_W * count) / (count + 1);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="forecast-svg-chart">
      {/* Grid lines */}
      {[0, 0.5, 1].map(t => {
        const y = PAD.top + (1 - t) * innerH;
        return (
          <line key={t} x1={PAD.left} y1={y} x2={PAD.left + innerW} y2={y}
            style={{ stroke: "var(--border)" }} strokeWidth={t === 1 ? 0.5 : 0.4}
            strokeDasharray={t === 0.5 ? "3 2" : undefined} />
        );
      })}

      {vals.map((v, i) => {
        const ratio = maxVal > 0 ? v / maxVal : 0;
        const barH  = Math.max(ratio * innerH, 2);
        const x     = PAD.left + GAP * (i + 1) + BAR_W * i;
        const y     = PAD.top + innerH - barH;
        const col   = i === 0 ? "var(--blue)" : i === 1 ? "var(--green)" : "var(--yellow)";

        return (
          <g key={i}>
            <rect x={x} y={y} width={BAR_W} height={barH}
              style={{ fill: col }} opacity={0.85} rx={2} />
            <text x={x + BAR_W / 2} y={y - 4} textAnchor="middle"
              fontSize={8} style={{ fill: col }} fontWeight={700}>{fmtVol(v)}</text>
            <text x={x + BAR_W / 2} y={H - 5} textAnchor="middle"
              fontSize={8.5} style={{ fill: "var(--text-dim)" }}>{HORIZON_LABEL[HORIZONS[i]]}</text>
          </g>
        );
      })}
    </svg>
  );
}

// ── Bar view (default) ────────────────────────────────────────────────────────

function VolBars({ vals, maxVal }: { vals: number[]; maxVal: number }) {
  return (
    <div className="vol-bars">
      {HORIZONS.map((h, i) => {
        const v   = vals[i];
        const pct = maxVal > 0 ? (v / maxVal) * 100 : 0;
        const col = i === 0 ? "var(--blue)" : i === 1 ? "var(--green)" : "var(--yellow)";
        return (
          <div key={h} className="vol-bar-row">
            <span className="vol-bar-horizon">{HORIZON_LABEL[h]}</span>
            <div className="vol-bar-track">
              <div className="vol-bar-fill" style={{ width: `${pct}%`, background: col }} />
            </div>
            <span className="vol-bar-val" style={{ color: col }}>{fmtVol(v)}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

export function ForecastSparkline({ data }: Props) {
  const [chartMode, setChartMode] = useState(false);
  const { short_term_vol, current_activity } = data;

  if (!short_term_vol) return null;

  const vals   = HORIZONS.map(h => short_term_vol[h] ?? 0);
  const maxVal = Math.max(...vals);
  if (maxVal === 0) return null;

  return (
    <div className="forecast-sparkline">
      <div className="forecast-header">
        <span className="intel-label">VOL ACTIVITY</span>
        {current_activity && (
          <span className="activity-badge" style={{ color: ACTIVITY_COL[current_activity] }}>
            {current_activity.toUpperCase()}
          </span>
        )}
        <span className="forecast-subtext">avg vol / 5min bar</span>
        <button
          className={`horizon-view-toggle${chartMode ? " horizon-view-toggle--active" : ""}`}
          onClick={() => setChartMode(v => !v)}
          title={chartMode ? "Switch to bars" : "Switch to chart"}
        >
          {chartMode ? "≡" : "⌁"}
        </button>
      </div>

      {chartMode
        ? <VolChart vals={vals} maxVal={maxVal} />
        : <VolBars  vals={vals} maxVal={maxVal} />
      }
    </div>
  );
}
