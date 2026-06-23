import type { Correlation, Divergence } from "../types";

interface Props {
  correlations: Correlation[];
  divergence: Divergence[];
  onClose: () => void;
}

function rColor(r: string | null): string {
  if (r == null) return "#888";
  const v = parseFloat(r);
  if (v >= 0.7) return "#4caf50";
  if (v <= -0.7) return "#f44336";
  if (Math.abs(v) >= 0.4) return "#ff9800";
  return "#aaa";
}

function rLabel(r: string | null): string {
  if (r == null) return "—";
  return parseFloat(r).toFixed(3);
}

export function CorrelationPanel({ correlations, divergence, onClose }: Props) {
  const top = correlations.slice(0, 20);

  return (
    <div className="side-panel">
      <div className="side-panel-header">
        <h3>Cross-Asset Intelligence</h3>
        <button className="panel-close" onClick={onClose}>✕</button>
      </div>

      {divergence.length > 0 && (
        <section className="corr-section">
          <h4 className="corr-section-title">Source Divergence (CoinGecko vs Coinbase)</h4>
          <table className="corr-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>CoinGecko</th>
                <th>Coinbase</th>
                <th>Gap (bps)</th>
              </tr>
            </thead>
            <tbody>
              {divergence.map((d) => {
                const gap = parseFloat(d.gap_bps);
                const gapCls = gap > 100 ? "div-gap--high" : gap > 30 ? "div-gap--mid" : "";
                return (
                  <tr key={d.instrument_id}>
                    <td className="corr-symbol">{d.symbol}</td>
                    <td>{parseFloat(d.price_coingecko).toLocaleString("en-US", { maximumFractionDigits: 2 })}</td>
                    <td>{parseFloat(d.price_coinbase).toLocaleString("en-US", { maximumFractionDigits: 2 })}</td>
                    <td className={`div-gap ${gapCls}`}>{gap.toFixed(1)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}

      <section className="corr-section">
        <h4 className="corr-section-title">Top Correlations (30d daily returns)</h4>
        <table className="corr-table">
          <thead>
            <tr>
              <th>Pair</th>
              <th>r</th>
              <th>n</th>
            </tr>
          </thead>
          <tbody>
            {top.map((c) => (
              <tr key={`${c.instrument_id_a}-${c.instrument_id_b}`}>
                <td className="corr-symbol">
                  {c.symbol_a} / {c.symbol_b}
                </td>
                <td style={{ color: rColor(c.pearson_r), fontWeight: 600 }}>
                  {rLabel(c.pearson_r)}
                </td>
                <td className="corr-n">{c.sample_count ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
