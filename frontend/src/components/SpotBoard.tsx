import { useState } from "react";
import type { IntelSnapshot, MLInstrumentSignal, SpotPrice, VolumeInstrumentForecast } from "../types";
import { useSpotPrices } from "../hooks/useSpotPrices";
import { useWatchlist } from "../hooks/useWatchlist";
import { useAlerts } from "../hooks/useAlerts";
import { useIntel } from "../hooks/useIntel";
import { useForecast } from "../hooks/useForecast";
import { useSignals } from "../hooks/useSignals";
import { useTheme } from "../hooks/useTheme";
import { InstrumentRow } from "./InstrumentRow";
import { AlertPanel } from "./AlertPanel";
import { QuickConvert } from "./QuickConvert";
import { CorrelationPanel } from "./CorrelationPanel";
import { ToastContainer } from "./Toast";
import "./SpotBoard.css";

const COL_COUNT = 9;

interface BoardTableProps {
  title: string;
  items: SpotPrice[];
  starred: Set<number>;
  onToggleStar: (id: number) => void;
  onAlertClick: (id: number) => void;
  snapshotMap: Record<number, IntelSnapshot>;
  forecastMap: Record<number, VolumeInstrumentForecast>;
  signalMap: Record<number, MLInstrumentSignal>;
}

function BoardTable({
  title,
  items,
  starred,
  onToggleStar,
  onAlertClick,
  snapshotMap,
  forecastMap,
  signalMap,
}: BoardTableProps) {
  if (items.length === 0) return null;
  return (
    <section className="board-section">
      <h2 className="section-title">{title}</h2>
      <table className="board-table">
        <thead>
          <tr>
            <th className="col-star" />
            <th>Symbol</th>
            <th className="col-price">Price (USD)</th>
            <th className="col-change">1h %</th>
            <th className="col-change">24h %</th>
            <th className="col-change">7d %</th>
            <th className="col-regime">Regime</th>
            <th>Source</th>
            <th className="col-alert" />
          </tr>
        </thead>
        <tbody>
          {items.map((spot) => (
            <InstrumentRow
              key={spot.symbol}
              spot={spot}
              starred={starred.has(spot.instrument_id)}
              onToggleStar={onToggleStar}
              onAlertClick={onAlertClick}
              intel={snapshotMap[spot.instrument_id] ?? null}
              colCount={COL_COUNT}
              volForecast={forecastMap[spot.instrument_id] ?? null}
              mlSignal={signalMap[spot.instrument_id] ?? null}
            />
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function SpotBoard() {
  const { data, error, isLoading } = useSpotPrices();
  const { starred, toggle: toggleStar } = useWatchlist();
  const { alerts, triggered, addAlert, removeAlert, dismissTriggered } =
    useAlerts(data);
  const { intel } = useIntel();
  const { forecast } = useForecast();
  const { signals } = useSignals();
  const { theme, toggle: toggleTheme } = useTheme();

  const [showWatchlist, setShowWatchlist] = useState(false);
  const [showAlertPanel, setShowAlertPanel] = useState(false);
  const [alertPreselect, setAlertPreselect] = useState<number | undefined>();
  const [showConvert, setShowConvert] = useState(false);
  const [showCorrelation, setShowCorrelation] = useState(false);

  if (isLoading) return <div className="board-state">Loading…</div>;
  if (error)
    return (
      <div className="board-state board-state--error">
        Failed to load prices. Retrying…
      </div>
    );
  if (!data) return null;

  const allInstruments = [...data.fx, ...data.crypto];
  const snapshotMap: Record<number, IntelSnapshot> = intel?.snapshots ?? {};
  const forecastMap: Record<number, VolumeInstrumentForecast> = forecast?.instruments ?? {};
  const signalMap: Record<number, MLInstrumentSignal> = (signals as Record<number, MLInstrumentSignal>) ?? {};

  const fxItems = showWatchlist
    ? data.fx.filter((s) => starred.has(s.instrument_id))
    : data.fx;
  const cryptoItems = showWatchlist
    ? data.crypto.filter((s) => starred.has(s.instrument_id))
    : data.crypto;

  const starCount = starred.size;

  function handleAlertClick(id: number) {
    setAlertPreselect(id);
    setShowAlertPanel(true);
    setShowConvert(false);
    setShowCorrelation(false);
  }

  return (
    <>
      <ToastContainer toasts={triggered} onDismiss={dismissTriggered} />

      <div className="spot-board">
        <header className="board-header">
          <h1>NasSpot</h1>
          <span className="board-ts">
            Board as of {new Date(data.board_ts).toLocaleTimeString()}
          </span>
          <div className="header-actions">
            <button
              className="hdr-btn hdr-btn--theme"
              onClick={toggleTheme}
              title="Toggle light / dark mode"
            >
              {theme === "dark" ? "Light" : "Dark"}
            </button>
            <button
              className={`hdr-btn${showWatchlist ? " hdr-btn--active" : ""}`}
              onClick={() => setShowWatchlist((v) => !v)}
              title="Toggle watchlist filter"
            >
              {showWatchlist ? "★" : "☆"} Starred
              {starCount > 0 && (
                <span className="hdr-badge">{starCount}</span>
              )}
            </button>
            <button
              className={`hdr-btn${showAlertPanel ? " hdr-btn--active" : ""}`}
              onClick={() => {
                setShowAlertPanel((v) => !v);
                setShowConvert(false);
                setShowCorrelation(false);
              }}
              title="Manage alerts"
            >
              Alerts
              {alerts.length > 0 && (
                <span className="hdr-badge">{alerts.length}</span>
              )}
            </button>
            <button
              className={`hdr-btn${showConvert ? " hdr-btn--active" : ""}`}
              onClick={() => {
                setShowConvert(true);
                setShowAlertPanel(false);
                setShowCorrelation(false);
              }}
              title="FX quick convert"
            >
              Convert
            </button>
            <button
              className={`hdr-btn${showCorrelation ? " hdr-btn--active" : ""}`}
              onClick={() => {
                setShowCorrelation(true);
                setShowAlertPanel(false);
                setShowConvert(false);
              }}
              title="Cross-asset correlations"
              disabled={!intel}
            >
              Intel
              {intel && <span className="hdr-badge">{intel.correlations.length}</span>}
            </button>
          </div>
        </header>

        {showWatchlist && starCount === 0 && (
          <div className="watchlist-empty">
            No starred instruments — click ☆ on any row to add.
          </div>
        )}

        <BoardTable
          title="FX"
          items={fxItems}
          starred={starred}
          onToggleStar={toggleStar}
          onAlertClick={handleAlertClick}
          snapshotMap={snapshotMap}
          forecastMap={{}}
          signalMap={signalMap}
        />
        <BoardTable
          title="Crypto"
          items={cryptoItems}
          starred={starred}
          onToggleStar={toggleStar}
          onAlertClick={handleAlertClick}
          snapshotMap={snapshotMap}
          forecastMap={forecastMap}
          signalMap={signalMap}
        />
      </div>

      {showAlertPanel && (
        <AlertPanel
          alerts={alerts}
          allInstruments={allInstruments}
          preselect={alertPreselect}
          onAdd={addAlert}
          onRemove={removeAlert}
          onClose={() => setShowAlertPanel(false)}
        />
      )}

      {showConvert && (
        <QuickConvert
          fxPrices={data.fx}
          onClose={() => setShowConvert(false)}
        />
      )}

      {showCorrelation && intel && (
        <CorrelationPanel
          correlations={intel.correlations}
          divergence={intel.divergence}
          onClose={() => setShowCorrelation(false)}
        />
      )}
    </>
  );
}
