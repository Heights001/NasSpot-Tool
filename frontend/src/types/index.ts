export interface FreshnessInfo {
  source: string;
  source_ts: string | null;
  fetched_at: string;
  is_realtime: boolean;
  market_state: "open" | "closed" | "weekend_gap";
  age_seconds: number | null;
}

export interface SpotPrice {
  instrument_id: number;
  symbol: string;
  display_name: string;
  asset_class: "fx" | "crypto";
  price: string | null;
  bid: string | null;
  ask: string | null;
  display_precision: number;
  is_peg_watch: boolean;
  change_1h: string | null;
  change_24h: string | null;
  change_7d: string | null;
  freshness: FreshnessInfo | null;
}

export interface SpotBoardResponse {
  fx: SpotPrice[];
  crypto: SpotPrice[];
  board_ts: string;
}

export interface IntelSnapshot {
  instrument_id: number;
  symbol: string;
  computed_at: string;
  sample_count: number | null;
  rv_30d: string | null;
  rv_regime: "low" | "normal" | "high" | "extreme" | null;
  z_score: string | null;
  price_pctile_30d: string | null;
  spread_bps: string | null;
  rsi_14: string | null;
  bb_pct_b: string | null;
  sma_trend: "bullish" | "bearish" | null;
  ta_composite: "lean_long" | "lean_short" | "neutral" | "suppressed" | null;
  ta_reasoning: string | null;
}

export interface Correlation {
  instrument_id_a: number;
  instrument_id_b: number;
  symbol_a: string;
  symbol_b: string;
  pearson_r: string | null;
  sample_count: number | null;
}

export interface Divergence {
  instrument_id: number;
  symbol: string;
  price_coingecko: string;
  price_coinbase: string;
  gap_bps: string;
}

export interface IntelResponse {
  snapshots: Record<number, IntelSnapshot>;
  correlations: Correlation[];
  divergence: Divergence[];
  computed_at: string;
}

export interface VolumeForecastHour {
  ts: string;
  p25: number;
  p50: number;
  p75: number;
}

export interface VolumeInstrumentForecast {
  symbol: string;
  current_volume: number | null;
  current_activity: "busy" | "typical" | "quiet" | null;
  forecast: VolumeForecastHour[];
}

export interface ForecastResponse {
  generated_at: string | null;
  instruments: Record<number, VolumeInstrumentForecast>;
}

export interface MLHorizonPrediction {
  prob_up: number;
  signal: "bullish" | "bearish" | "neutral";
  confidence: "high" | "medium" | "low";
}

export interface MLInstrumentSignal {
  symbol: string;
  is_peg: boolean;
  predictions: Record<number, MLHorizonPrediction>;  // keyed by horizon_minutes
}

export type SignalsResponse = Record<number, MLInstrumentSignal>;  // keyed by instrument_id

export interface Alert {
  id: string;
  instrument_id: number;
  symbol: string;
  type: "threshold" | "peg";
  threshold?: number;
  direction?: "above" | "below";
  created_at: string;
}
