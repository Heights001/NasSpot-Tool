
const REGIME_COLORS: Record<string, string> = {
  low: "#4caf50",
  normal: "#2196f3",
  high: "#ff9800",
  extreme: "#f44336",
};

interface Props {
  regime: string | null;
}

export function RegimeBadge({ regime }: Props) {
  if (!regime) return <span className="regime-badge regime-badge--null">—</span>;
  const color = REGIME_COLORS[regime] ?? "#888";
  return (
    <span
      className="regime-badge"
      style={{ background: color }}
      title={`Volatility regime: ${regime}`}
    >
      {regime}
    </span>
  );
}
