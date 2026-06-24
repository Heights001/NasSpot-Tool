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

function HourlySparkline({ forecast, current_activity, current_volume }: {
  forecast: VolumeForecastHour[];
  current_activity: string | null;
  current_volume: number | null;
}) {
  const [chartMode, setChartMode] = useState(false);

  if (!forecast.length) return null;
  const maxVol  = Math.max(...forecast.map(f => f.p75));
  if (maxVol === 0) return null;
  const nowHour = new Date().getUTCHours();

  // ── Default: detailed line + band chart ──
  const W = 240, H = 92;
  const PAD = { top: 10, right: 8, bottom: 22, left: 36 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const n      = forecast.length;
  const scaleX  = (i: number) => PAD.left + (i / (n - 1)) * innerW;
  const scaleY  = (v: number) => PAD.top + innerH - (v / maxVol) * innerH;

  const areaTop    = forecast.map((f, i) => `${i === 0 ? "M" : "L"} ${scaleX(i).toFixed(1)} ${scaleY(f.p75).toFixed(1)}`).join(" ");
  const areaBottom = [...forecast].reverse().map((f, i) => `L ${scaleX(n - 1 - i).toFixed(1)} ${scaleY(f.p25).toFixed(1)}`).join(" ");
  const areaPath   = `${areaTop} ${areaBottom} Z`;
  const linePath   = forecast.map((f, i) => `${i === 0 ? "M" : "L"} ${scaleX(i).toFixed(1)} ${scaleY(f.p50).toFixed(1)}`).join(" ");
  const xTicks     = [0, 5, 11, 17, 23];
  const yTicks     = [0, 0.5, 1];

  // ── Toggle: diverging bar chart (each hour vs 24h average) ──
  const W_D = 240, H_D = 148;
  const PD  = { top: 8, right: 44, bottom: 14, left: 30 };
  const iW  = W_D - PD.left - PD.right;
  const iH  = H_D - PD.top - PD.bottom;
  const BAR_H   = Math.floor(iH / n) - 1;
  const centerX = PD.left + iW / 2;
  const avg     = forecast.reduce((s, f) => s + f.p50, 0) / n;
  const maxDev  = Math.max(...forecast.map(f => Math.abs(f.p50 - avg)), 1);
  const labelIdxs = new Set([0, 5, 11, 17, 23]);

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
        <button
          className={`horizon-view-toggle${chartMode ? " horizon-view-toggle--active" : ""}`}
          onClick={() => setChartMode(v => !v)}
          title={chartMode ? "Switch to line chart" : "Switch to diverging chart"}
        >
          {chartMode ? "≡" : "⌁"}
        </button>
      </div>

      {!chartMode ? (
        /* Default: line + band */
        <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="forecast-svg-chart">
          {yTicks.map(t => {
            const y = PAD.top + (1 - t) * innerH;
            return (
              <g key={t}>
                <line x1={PAD.left} y1={y} x2={PAD.left + innerW} y2={y}
                  style={{ stroke: "var(--border)" }} strokeWidth={0.5}
                  strokeDasharray={t === 0.5 ? "3 2" : undefined} />
                <text x={PAD.left - 4} y={y + 3.5} textAnchor="end"
                  fontSize={7.5} style={{ fill: "var(--text-dim)" }}>
                  {fmtVol(maxVol * t)}
                </text>
              </g>
            );
          })}
          <path d={areaPath} style={{ fill: "var(--blue)" }} opacity={0.12} />
          <path d={linePath} fill="none" style={{ stroke: "var(--blue)" }}
            strokeWidth={1.5} strokeLinejoin="round" />
          {forecast.map((f, i) => {
            if (new Date(f.ts).getUTCHours() !== nowHour) return null;
            return <circle key={i} cx={scaleX(i)} cy={scaleY(f.p50)} r={3.5}
              style={{ fill: "var(--blue)" }} />;
          })}
          {xTicks.map(i => (
            <text key={i} x={scaleX(i)} y={H - 5} textAnchor="middle"
              fontSize={7.5} style={{ fill: "var(--text-dim)" }}>+{i + 1}h</text>
          ))}
        </svg>
      ) : (
        /* Diverging: each hour vs 24h avg */
        <svg viewBox={`0 0 ${W_D} ${H_D}`} width={W_D} height={H_D} className="forecast-svg-chart">
          {/* Axis labels */}
          <text x={PD.left}      y={H_D - 2} textAnchor="middle" fontSize={7.5} style={{ fill: "var(--text-dim)" }}>LOW</text>
          <text x={centerX}      y={H_D - 2} textAnchor="middle" fontSize={7.5} style={{ fill: "var(--text-dim)" }}>AVG</text>
          <text x={W_D - PD.right} y={H_D - 2} textAnchor="middle" fontSize={7.5} style={{ fill: "var(--text-dim)" }}>HIGH</text>
          {/* Center divider */}
          <line x1={centerX} y1={PD.top} x2={centerX} y2={H_D - PD.bottom}
            style={{ stroke: "var(--border)" }} strokeWidth={1} strokeDasharray="3 2" />
          {forecast.map((f, i) => {
            const y         = PD.top + i * (BAR_H + 1);
            const dev       = f.p50 - avg;
            const barW      = Math.abs(dev) / maxDev * (iW / 2);
            const barX      = dev >= 0 ? centerX : centerX - barW;
            const isCurrent = new Date(f.ts).getUTCHours() === nowHour;
            const col       = isCurrent ? "var(--yellow)" : dev >= 0 ? "var(--blue)" : "var(--text-dim)";
            return (
              <g key={i}>
                <rect x={PD.left} y={y} width={iW} height={BAR_H}
                  style={{ fill: "var(--surface2)" }} rx={1} />
                <rect x={barX} y={y} width={Math.max(barW, 1)} height={BAR_H}
                  style={{ fill: col }} opacity={0.85} rx={1} />
                {labelIdxs.has(i) && (
                  <text x={PD.left - 3} y={y + BAR_H / 2 + 3}
                    textAnchor="end" fontSize={7} style={{ fill: "var(--text-dim)" }}>
                    +{i + 1}h
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      )}
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
