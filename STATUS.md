# NasSpot — STATUS.md

**Last updated:** 2026-06-23  
**Phase:** SHIPPED — M1–M4 complete, deployed to Railway + Vercel

**Production URLs:**
- Frontend: https://nasspottool-v1.vercel.app
- Backend API: https://nasspot-api-production.up.railway.app
- GitHub: https://github.com/Heights001/NasSpot-Tool

**GH Actions secrets required** (Settings → Secrets → Actions in the GitHub repo):
- `DATABASE_URL` — same Neon URL as Railway env var
- `COINGECKO_DEMO_KEY` — same value as Railway env var

---

## Feasibility Results (2026-06-22 05:39 UTC, Sunday)

| Source | Instrument | Median Staleness | Verdict |
|---|---|---|---|
| Twelve Data | EUR/USD | 31,200s | WEEKEND_GAP (market closed) |
| Twelve Data | USD/JPY | 31,201s | WEEKEND_GAP (market closed) |
| Twelve Data | GBP/USD | 31,202s | WEEKEND_GAP (market closed) |
| CoinGecko | BTC | 20.2s | REAL-TIME-ish |
| CoinGecko | ETH | 20.2s | REAL-TIME-ish |
| CoinGecko | SOL | 20.2s | REAL-TIME-ish |
| CoinGecko | XRP | 21.2s | REAL-TIME-ish |

**Cross-source divergence (CoinGecko vs Coinbase):** BTC 4.1 bps, ETH 3.1 bps — normal.

### Decisions

- FX staleness of ~31,200s is because FX is closed on weekends (24/5). Not a feed problem.  
  The `market_state` service badges FX as `weekend_gap` on Sat/Sun and skips refresh.  
  **Re-run feasibility on a weekday to measure actual trading-hours staleness.**
- **CRYPTO_TTL = 30s** (CoinGecko updates ~every 20s; 30s gives a small headroom).
- **FX_TTL = 60s** during market hours (placeholder until weekday recheck).
- **Cross-source divergence threshold: 50 bps** (3–4 bps is normal noise).
- Twelve Data 2/5 success on some pairs during feasibility = rate-limit from rapid polling.  
  Single-flight + TTL avoids this in production.

---

## M1 Status

- [x] Feasibility check complete  
- [x] STATUS.md written  
- [x] Backend scaffolded (FastAPI + SQLAlchemy + Alembic)  
- [x] DB migrations run  
- [x] Instruments seeded (14 FX active, 7 crypto; DXY disabled — not in TwelveData free tier)  
- [x] `/spot` board endpoint smoke-tested: 14 FX + 7 crypto, freshness badges, peg-watch flags  
- [x] Batch upstream fetches: one CoinGecko call for all 7 crypto, two TwelveData calls for 14 FX  
- [x] Cold-start latency: ~12s (Neon waking from sleep); warm: ~6s (batch upstream + single commit)  
- [x] Frontend scaffolded (React/Vite PWA → `frontend/`)  
- [x] End-to-end smoke test (local) — board renders, SWR auto-refresh confirmed at 30s interval

## M2 Status

- [x] Change windows: 1h/24h/7d on board — crypto via CoinGecko `/coins/markets`; FX 24h via TwelveData `percent_change`
- [x] Watchlist — localStorage (`nasspot_watchlist`), star/unstar per row, filter toggle with badge count
- [x] In-app alerts — threshold (above/below price) + peg-break (>0.5% from $1), localStorage, toast on trigger
- [x] FX quick-convert — pair selector, live rate, bidirectional input, ⇄ flip

### M2 notes (2026-06-22)

- CoinGecko switched from `/simple/price` → `/coins/markets` to get 1h/24h/7d change in one call
- TwelveData `percent_change` field = 24h change; 1h/7d show "—" for FX (not on free tier)
- TwelveData hit 800/day credit limit during development — FX change_24h populates on daily reset
- Alerts fire once per session (tracked in `firedRef`); re-added alert fires again
- Side panels (Alerts + Convert) share `.side-panel` CSS shell — mutually exclusive, close one to open other

## M3 Status

- [x] History seed: 30d daily from CoinGecko (crypto) + Yahoo Finance (FX) → `price_history`
- [x] `intel_snapshot` + `intel_correlation` tables (Alembic migration 002)
- [x] RV 30d (annualized), regime bands (low/normal/high/extreme), z-score, percentile, spread bps
- [x] 190 Pearson correlations (all 21×20/2 instrument pairs, 30d daily log returns)
- [x] Coinbase public ticker as second source for BTC/ETH/SOL/XRP — divergence in bps
- [x] `GET /intel` with 4h lazy TTL recompute; `POST /intel/seed` for history bootstrap
- [x] Frontend: `RegimeBadge` per row, expandable intel drawer (click symbol), `CorrelationPanel` with divergence table + top-20 sorted by |r|, `Intel [190]` header button

### M3 notes (2026-06-22)

- Intel TTL 4h — analytics don't change minute-to-minute; SWR polls at 5min
- `intel_correlation` always stores pair with `instrument_id_a < instrument_id_b`
- RV regime thresholds: crypto low<40%/normal<80%/high<120%/extreme≥120%; FX low<5%/normal<10%/high<20%/extreme≥20%
- Coinbase public ticker: `/v2/prices/{product_id}/spot`, keyless, maps from CoinGecko IDs
- Yahoo Finance FX history: `query1.finance.yahoo.com/v8/finance/chart/{EURUSD=X}?interval=1d&range=30d` + `User-Agent` header
- USD/CNH showed "—" regime (Yahoo returned no data for USDCNH=X — may need USDCNH=X vs CNH=X)

## M4 Status

- [x] `volume_history` + `volume_forecast` tables (Alembic migration 003)
- [x] 30d hourly volume from CoinGecko `/coins/{id}/market_chart?days=30` — auto-granularity returns hourly for ≤90d; 721 rows per instrument
- [x] Seasonal quantile model: group by (hour_of_day, weekday) → p25/p50/p75 from historical volumes; pure Python, no scipy
- [x] `POST /forecast/seed` — bootstrap history + run model; `GET /forecast` — return latest 24h forecast
- [x] Activity badge: compare current 24h volume to nearest forecast-slot p25/p75 → BUSY/TYPICAL/QUIET
- [x] `scripts/run_forecast.py` — standalone GH Actions entry point
- [x] `.github/workflows/volume_forecast.yml` — daily cron at 00:30 UTC + workflow_dispatch
- [x] Frontend: `useForecast` hook (6h SWR refresh), `ForecastSparkline` SVG (24 bars, p25-p75 band + p50 marker, current-hour highlight), rendered in intel drawer for all crypto rows
- [x] GH Actions secrets required: `DATABASE_URL`, `COINGECKO_DEMO_KEY`

### M4 notes (2026-06-22)

- Volume data is 24h rolling from CoinGecko — model forecasts "typical 24h volume at this hour of this weekday"
- Seasonal model needs ≥2 samples per (hour, weekday) bucket; falls back to same-hour nearest weekday if bucket empty
- Activity badge uses current-hour forecast slot; updates as new forecast runs daily
- Forecast SWR poll: 6h (model only updates once/day via GH Actions)
- All 7 crypto instruments seeded (BTC/ETH/SOL/XRP/BNB/USDT/USDC); stablecoins show very low RV which is expected

### Backend notes (2026-06-22)

- `async_database_url` converts `sslmode=require` → `ssl=require` for asyncpg; strips `channel_binding`  
- `alembic/env.py` uses `settings.async_database_url` (fixed from inline replace)  
- `market_state.py` requires `from __future__ import annotations` for Python 3.9 union syntax  
- TwelveData free plan: 8 API calls/min, 800/day, max 8 symbols/batch → 2 batches for 14 FX pairs with 1.5s inter-batch delay  
- DXY: symbol not available on TwelveData free; instrument disabled in DB  
- Board uses `get_board_prices()` (single-commit batch refresh) not per-instrument `get_or_refresh()`
