import type { FreshnessInfo } from "../types";

interface Props {
  freshness: FreshnessInfo | null;
}

const STATE_LABEL: Record<string, string> = {
  open: "",
  closed: "CLOSED",
  weekend_gap: "WEEKEND",
};

export function FreshnessTag({ freshness }: Props) {
  if (!freshness) return <span className="freshness freshness--unknown">NO DATA</span>;

  const stateLabel = STATE_LABEL[freshness.market_state] ?? freshness.market_state.toUpperCase();
  const ageLabel =
    freshness.age_seconds != null
      ? freshness.age_seconds < 60
        ? `${Math.round(freshness.age_seconds)}s ago`
        : `${Math.round(freshness.age_seconds / 60)}m ago`
      : null;

  const isStale = (freshness.age_seconds ?? 0) > 120;
  const isOffMarket = freshness.market_state !== "open";

  return (
    <span
      className={`freshness ${
        isOffMarket
          ? "freshness--offmarket"
          : isStale
          ? "freshness--stale"
          : "freshness--live"
      }`}
    >
      {freshness.source}
      {stateLabel ? ` · ${stateLabel}` : ""}
      {ageLabel ? ` · ${ageLabel}` : ""}
    </span>
  );
}
