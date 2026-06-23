import type { VolumeForecastHour, VolumeInstrumentForecast } from "../types";

const W = 240;
const H = 44;
const TOP_PAD = 4;
const USABLE_H = H - TOP_PAD;
const STEP = W / 24;
const BAR_W = Math.max(1, STEP - 1.5);

function fmtVol(v: number): string {
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toFixed(0)}`;
}

interface Props {
  data: VolumeInstrumentForecast;
}

export function ForecastSparkline({ data }: Props) {
  const { forecast, current_volume, current_activity } = data;
  if (!forecast.length) return null;

  const maxVol = Math.max(...forecast.map((f) => f.p75));
  if (maxVol === 0) return null;

  const nowHour = new Date().getUTCHours();

  function scaleY(v: number): number {
    return TOP_PAD + USABLE_H - (v / maxVol) * USABLE_H;
  }

  const activityColor: Record<string, string> = {
    busy: "#22c55e",
    typical: "#3b82f6",
    quiet: "#666",
  };

  return (
    <div className="forecast-sparkline">
      <div className="forecast-header">
        <span className="intel-label">VOL 24H FORECAST</span>
        {current_activity && (
          <span
            className="activity-badge"
            style={{ color: activityColor[current_activity] }}
          >
            {current_activity.toUpperCase()}
          </span>
        )}
        {current_volume != null && (
          <span className="forecast-current-vol">{fmtVol(current_volume)}</span>
        )}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className="forecast-svg">
        {forecast.map((f, i) => {
          const x = i * STEP;
          const y75 = scaleY(f.p75);
          const y50 = scaleY(f.p50);
          const y25 = scaleY(f.p25);
          const horizHour = new Date(f.ts).getUTCHours();
          const isCurrent = horizHour === nowHour;

          return (
            <g key={i}>
              {/* uncertainty band (p25–p75) */}
              <rect
                x={x}
                y={y75}
                width={BAR_W}
                height={Math.max(1, y25 - y75)}
                fill={isCurrent ? "rgba(59,130,246,0.25)" : "rgba(255,255,255,0.08)"}
              />
              {/* p50 marker */}
              <rect
                x={x}
                y={y50 - 1}
                width={BAR_W}
                height={3}
                fill={isCurrent ? "#3b82f6" : "rgba(255,255,255,0.35)"}
              />
            </g>
          );
        })}
      </svg>
      <div className="forecast-labels">
        <span>+1h</span>
        <span>+12h</span>
        <span>+24h</span>
      </div>
    </div>
  );
}
