import { useState } from "react";
import type { IntelSnapshot, SpotPrice, VolumeInstrumentForecast } from "../types";
import { FreshnessTag } from "./FreshnessTag";
import { RegimeBadge } from "./RegimeBadge";
import { ForecastSparkline } from "./ForecastSparkline";
import SignalBadge from "./SignalBadge";

interface Props {
  spot: SpotPrice;
  starred: boolean;
  onToggleStar: (id: number) => void;
  onAlertClick: (id: number) => void;
  intel: IntelSnapshot | null;
  colCount: number;
  volForecast: VolumeInstrumentForecast | null;
}

function formatPrice(price: string | null, precision: number): string {
  if (price == null) return "—";
  const n = parseFloat(price);
  if (isNaN(n)) return "—";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  });
}

function formatChange(change: string | null): { label: string; cls: string } {
  if (change == null) return { label: "—", cls: "change--null" };
  const n = parseFloat(change);
  if (isNaN(n)) return { label: "—", cls: "change--null" };
  const sign = n > 0 ? "+" : "";
  return {
    label: `${sign}${n.toFixed(2)}%`,
    cls: n > 0 ? "change--up" : n < 0 ? "change--down" : "",
  };
}

function fmt(v: string | null, decimals = 2): string {
  if (v == null) return "—";
  const n = parseFloat(v);
  return isNaN(n) ? "—" : n.toFixed(decimals);
}

export function InstrumentRow({
  spot,
  starred,
  onToggleStar,
  onAlertClick,
  intel,
  colCount,
  volForecast,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const hasDrawer = !!(intel || volForecast);
  const c1h = formatChange(spot.change_1h);
  const c24h = formatChange(spot.change_24h);
  const c7d = formatChange(spot.change_7d);

  return (
    <>
      <tr
        className={`instrument-row${expanded ? " instrument-row--expanded" : ""}`}
      >
        <td className="col-star">
          <button
            className={`star-btn${starred ? " star-btn--on" : ""}`}
            onClick={() => onToggleStar(spot.instrument_id)}
            title={starred ? "Remove from watchlist" : "Add to watchlist"}
          >
            {starred ? "★" : "☆"}
          </button>
        </td>
        <td className="col-symbol" onClick={() => setExpanded((e) => !e)} style={{ cursor: hasDrawer ? "pointer" : undefined }}>
          <span className="symbol">{spot.symbol}</span>
          {spot.is_peg_watch && <span className="peg-badge">PEG</span>}
          {hasDrawer && <span className="expand-caret">{expanded ? "▾" : "▸"}</span>}
        </td>
        <td className="col-price">
          {formatPrice(spot.price, spot.display_precision)}
        </td>
        <td className={`col-change ${c1h.cls}`}>{c1h.label}</td>
        <td className={`col-change ${c24h.cls}`}>{c24h.label}</td>
        <td className={`col-change ${c7d.cls}`}>{c7d.label}</td>
        <td className="col-regime">
          <RegimeBadge regime={intel?.rv_regime ?? null} />
        </td>
        <td className="col-freshness">
          <FreshnessTag freshness={spot.freshness} />
        </td>
        <td className="col-alert">
          <button
            className="alert-btn"
            onClick={() => onAlertClick(spot.instrument_id)}
            title="Set alert"
          >
            &#9676;
          </button>
        </td>
      </tr>
      {expanded && hasDrawer && (
        <tr className="intel-drawer-row">
          <td colSpan={colCount}>
            <div className="intel-drawer">
              {intel && (
                <>
                  <div className="intel-stat">
                    <span className="intel-label">RV 30d</span>
                    <span className="intel-val">{fmt(intel.rv_30d, 4)}</span>
                  </div>
                  <div className="intel-stat">
                    <span className="intel-label">Z-Score</span>
                    <span
                      className={`intel-val${
                        intel.z_score
                          ? Math.abs(parseFloat(intel.z_score)) > 2
                            ? " intel-val--alert"
                            : ""
                          : ""
                      }`}
                    >
                      {fmt(intel.z_score, 2)}
                    </span>
                  </div>
                  <div className="intel-stat">
                    <span className="intel-label">30d %ile</span>
                    <span className="intel-val">{fmt(intel.price_pctile_30d, 1)}%</span>
                  </div>
                  <div className="intel-stat">
                    <span className="intel-label">Spread</span>
                    <span className="intel-val">
                      {intel.spread_bps ? `${fmt(intel.spread_bps, 1)} bps` : "—"}
                    </span>
                  </div>
                  <div className="intel-stat">
                    <span className="intel-label">Samples</span>
                    <span className="intel-val">{intel.sample_count ?? "—"}</span>
                  </div>
                  <SignalBadge snap={intel} />
                </>
              )}
              {volForecast && (
                <div className="intel-stat intel-stat--wide">
                  <ForecastSparkline data={volForecast} />
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
