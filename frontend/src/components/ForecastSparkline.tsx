import { useState } from "react";
import type { VolumeInstrumentForecast, VolumeForecastHour } from "../types";

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

// ── Hourly fallback sparkline (when intraday data unavailable) ────────────────

const W_SPARK = 240, H_SPARK = 44, TOP_PAD = 4;
const USABLE_H = H_SPARK - TOP_PAD;

function HourlySparkline({ forecast, current_activity, current_volume }: {
  forecast: VolumeForecastHour[];
  current_activity: string | null;
  current_volume: number | null;
}) {
  if (!forecast.length) return null;
  const STEP  = W_SPARK / 24;
  const BAR_W = Math.max(1, STEP - 1.5);
  const maxVol = Math.max(...forecast.map(f => f.p75));
  if (maxVol === 0) return null;
  const nowHour = new Date().getUTCHours();
  const scaleY = (v: number) => TOP_PAD + USABLE_H - (v / maxVol) * USABLE_H;

  return (
    <div className="forecast-sparkline">
      <div className="forecast-header">
        <span className="intel-label">VOL 24H FORECAST</span>
        {current_activity && (
          <span className="activity-badge" style={{ color: ACTIVITY_COL[current_activity] }}>
            {current_activity.toUpperCase()}
          </span>
        )}
        {current_volume != null && (
          <span className="forecast-subtext">{fmtVol(current_volume)}</span>
        )}
      </div>
      <svg viewBox={`0 0 ${W_SPARK} ${H_SPARK}`} width={W_SPARK} height={H_SPARK} className="forecast-svg">
        {forecast.map((f, i) => {
          const x = i * STEP;
          const isCurrent = new Date(f.ts).getUTCHours() === nowHour;
          return (
            <g key={i}>
              <rect x={x} y={scaleY(f.p75)} width={BAR_W}
                height={Math.max(1, scaleY(f.p25) - scaleY(f.p75))}
                fill={isCurrent ? "rgba(59,130,246,0.25)" : "rgba(255,255,255,0.08)"} />
              <rect x={x} y={scaleY(f.p50) - 1} width={BAR_W} height={3}
                fill={isCurrent ? "#3b82f6" : "rgba(255,255,255,0.35)"} />
            </g>
          );
        })}
      </svg>
      <div className="forecast-labels">
        <span>+1h</span><span>+12h</span><span>+24h</span>
      </div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

export function ForecastSparkline({ data }: Props) {
  const [chartMode, setChartMode] = useState(false);
  const { short_term_vol, current_activity, current_volume, forecast } = data;

  // Fall back to hourly sparkline when intraday data is not yet available
  if (!short_term_vol) {
    if (forecast.length > 0) {
      return <HourlySparkline forecast={forecast} current_activity={current_activity} current_volume={current_volume} />;
    }
    return null;
  }

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
