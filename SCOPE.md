# NasSpot — SCOPE.md

**Status:** Scoping complete → ready for Claude Code
**Owner:** Daniel
**Last updated:** 2026-06-21
**Sibling project:** NasVol Forecast (separate, untouched — no shared backend, no merge)
**Name:** NasSpot (renameable; one-string change). The *spot/price* sibling to NasVol's *volume/forecast*.

---

## 1. Overview & Positioning

NasSpot answers one question, present tense: **"What is this worth right now?"** — for a curated set of FX and crypto instruments, in USD, for a global financial-markets trader.

It is the **price** sibling to NasVol's **volume**: NasVol tells you how *busy* a market will be; NasSpot tells you what a market is *worth now*, and is upfront about how fresh and how certain that number is. Two separate products in the "Nas" family.

NasSpot is **descriptive, directive.** Its edge is *honesty and cross-asset clarity*,A prediction. A serious trader doesn't lack things shouting buy/sell at them — their terminal and ten apps already do that, mostly badly. What they lack is one brutally honest pane that says what's true right now and how sure it is, and surfaces relationships a single-asset screen hides. That restraint **is** the product.

> Tagline: *Spot-price truth and descriptive market intelligence for FX & crypto.*

---

## 2. Goals & Non-Goals

### Goals
- A fast, curated, multi-instrument spot board (FX + crypto), USD-quoted.
- **Freshness honesty** on every number — source, timestamp, real-time/delayed, market state.
- A **descriptive-intelligence layer** that makes the trader sharper: cross-asset regime read, rolling correlation, volatility/liquidity reads, peg monitoring, anomaly alerts.
- Ships and runs on **pure free tier** (Vercel + Railway + serverless Postgres), solo-maintainable.

### Non-Goals — the bright line (load-bearing, not optional)
- **No buy/sell signals or directional calls.**
- **No price prediction / forecasting.** The *only* forward-looking element is crypto **volume-activity** forecasting — how *busy*, with uncertainty bands — never price, never direction (Phase 4, stretch).
- **No order execution, brokerage, or money movement.**
- **No personalized investment advice.**

**Why this line holds:** on a free-tier, lazy-refresh, partly-unofficial-data stack, emitting directional calls or executing trades turns a useful reference tool into a liability with someone else's capital. Restraint = credibility. Honesty about uncertainty is the differentiator, not a gap.

---

## 3. Instruments (v1 — config; trivially trimmed or extended)

All quoted in USD.

**FX (~15)**
- Majors: EUR/USD, USD/JPY, GBP/USD, USD/CHF, AUD/USD, USD/CAD, NZD/USD
- Crosses: EUR/GBP, EUR/JPY, GBP/JPY
- Dollar gauge: DXY
- EM watch: USD/CNH, USD/MXN, USD/ZAR, USD/SGD

**Crypto (~7)**
- Majors: BTC, ETH
- Large caps: SOL, XRP, BNB
- Peg watch: USDT, USDC (monitored for deviation from $1)

*Optional:* USD/GHS (home pair) — off the global-trader thesis; include only on request.

---

## 4. Feature Set

### 4.1 Core Spot Board
- Live / near-live USD spot per instrument (lazy-refreshed — see §6).
- **Freshness honesty** on every figure: source + timestamp + real-time/delayed badge + market state. FX is ~24/5 with a weekend gap; crypto is 24/7 — so "stale vs just closed" is resolved per asset class.
- Per-instrument history + charts.
- One unified watchlist across FX and crypto.
- **Multi-source transparency** — sources shown side by side, never blended into one opaque composite.
- Change windows: 1h / 24h / 7d %.
- Bid/ask spread as a **liquidity tell** where the feed provides it (the FX/crypto analog of the commodity basis we dropped) — descriptive only.
- Correct precision per instrument: FX pip conventions; crypto high-decimal; stablecoins to basis-point deviation.
- **FX quick-convert** — amount across any watched pair at live rates.
- **Stablecoin peg monitor** — USDT/USDC deviation from $1, flagged on drift.
- **Price / threshold alerts** (in-app + PWA push).

### 4.2 Descriptive-Intelligence Layer — the "really smart" part (all descriptive, zero calls)
- **Cross-asset regime read** — dollar strength (DXY + basket) vs crypto risk appetite, surfaced as a *labeled descriptive read* ("dollar firm / crypto risk-on") derived from current observed data. Never a forecast.
- **Rolling correlation matrix** (e.g., 30-day) across watched instruments — which pairs move together, which have decoupled. Pure stats on history.
- **Volatility regime** — realized volatility per instrument (rolling, annualized), banded *calm / normal / elevated / extreme* relative to its **own** recent history. Informs risk and sizing awareness.
- **Liquidity read** — spread-as-liquidity-tell + "unusually thin / active vs typical" flags.
- **Cross-source divergence** — aggregated (CoinGecko) vs single-venue (Coinbase/Binance) crypto price gap beyond threshold; surfaced as *information* (venue stress / arb visibility), not a trade call.
- **Anomaly & threshold alerts** — flags *what changed*: peg drift, vol spike, unusual spread, large % move, correlation break. Ambient sentinel — never "what to do."
- **(Phase 4, stretch) Crypto volume-activity forecast** — NasVol-style expected market *activity* ahead, **with uncertainty bands**, crypto-only (FX has no consolidated volume to forecast). Forecasts *busy-ness*, never price/direction; helps the trader time *into* liquidity. A new model build — **not** the NasVol port.

**The throughline:** the intelligence lives in the honesty and the cross-asset read, not in a crystal ball. Every item above is descriptive of *now* or the *recent past*. It makes the trader sharper and trusts them to make the call.

---

## 5. Data Sources

Honesty-first. The per-asset-class adapter split also **spreads free quotas** so no single cap throttles the whole board.

| Leg | Primary source | Nature | Freshness (to verify) | Free limit |
|---|---|---|---|---|
| FX | Twelve Data | Genuine spot (cash FX) | Real-time on free for FX, rate-limited | 800 calls/day, 8/min |
| Crypto (reference) | CoinGecko | Aggregated across venues, methodology published | Near-real-time (cadence to measure) | ~10k calls/month (Demo) |
| Crypto (cross-check) | Coinbase / Binance public ticker | Single-venue, keyless | Real-time | Public endpoints |

- Both FX and crypto are **genuine spot** — no futures-proxy caveat — so the freshness badge is just source + timestamp + venue + market-state.
- Behind a **source-abstraction layer**: one adapter per provider; swapping to a licensed feed later is a config change (the VolForecast pattern).
- **Validate before building** with `feasibility_check.py` (§Deliverables) — measures real latency and timestamp staleness per source. We commit only to what it actually returns. *Don't claim "real-time" tighter than the script proves, and don't refresh faster than the source updates.*

---

## 6. Architecture (free-tier; no Redis, no worker)

- **Frontend:** React/Vite PWA → **Vercel (free)**. Unified board; per instrument a spot panel plus, where applicable, intelligence panels.
- **Backend:** FastAPI → **new Railway project** (isolated from NasVol). Modules: `spot`, `intel`, `alerts`.
- **Store:** **Serverless Postgres (Neon/Supabase free)** — NasSpot's own DB and system of record. Does double duty as latest-price cache *and* history store. *Not* a Railway Postgres service (saves a service slot + credit). Use the pooled connection string; expect a brief first-query wake when idle.
- **Freshness without a worker — lazy refresh-on-read (the keystone):** on a board read, serve latest from Postgres; if older than TTL (30–60s) *and* the market is open, fetch upstream, upsert, return fresh; else serve stored. **Single-flight** the upstream fetch with a Postgres advisory lock (`pg_advisory_xact_lock`) to prevent stampede — this is exactly what Redis would have done, done natively. API spend is bounded by the TTL window, not by user count. No background ingest worker required.
- **Scheduling:** none for live spot. Any periodic batch (Phase-4 crypto vol model; rolling-stat precompute) → **GitHub Actions cron** — fine for forward-looking batch; **not** used for live spot (5-min floor, runs drift 10–30 min). If sub-minute warm data is wanted later: a free cron-job.org ping → secret-protected `/internal/ingest`, market-hours only.
- **Redis:** none in v1. If rate-limiting / shared counters are needed later → **Upstash** (HTTP/REST, no Railway service to add; fails open), *not* a Railway Redis service.

---

## 7. Data Model (Postgres; `Decimal`/`NUMERIC` everywhere money touches)

- **`instruments`** — id, symbol, display_name, asset_class (`fx` | `crypto`), quote_ccy (USD), provider_symbol (per source), display_precision, is_active, sort_order, flags (e.g. `peg_watch`).
- **`latest_price`** — instrument_id (PK), price NUMERIC, bid NUMERIC, ask NUMERIC, source, source_ts TIMESTAMPTZ, fetched_at TIMESTAMPTZ, is_realtime BOOL, market_state (`open` | `closed` | `weekend_gap`), change_1h / change_24h / change_7d NUMERIC.
- **`price_history`** — instrument_id, ts TIMESTAMPTZ, price NUMERIC, source; (instrument_id, ts) indexed; append-only; powers charts + rolling stats.
- **`source_quote`** — instrument_id, source, price NUMERIC, source_ts, fetched_at — per-source rows for multi-source transparency + divergence (never blended).
- **`alerts`** — id, instrument_id, type (`threshold` | `peg` | `vol` | `divergence` | `pct_move`), condition (JSON), is_active, last_fired_at.
- **`intel_snapshot`** (optional) — periodic correlation / vol / regime computations cached off the hot path.

**Precision:** store FX/crypto as `NUMERIC(20,10)` (generous; **never float**); display via per-instrument `display_precision`. Stablecoin deviation tracked in basis points.

---

## 8. Conventions (persistent — carried from prior projects)
- Money/prices: **`Decimal`/`NUMERIC`, never float**, end to end. Parse provider strings → `Decimal` *before* use.
- Lazy-refresh single-flight via Postgres advisory lock; **fail-open** — a source outage serves last-known, clearly stamped stale; never a 500 on the board.
- Migrations are **run** (`alembic upgrade head`) after every model change, not just written.
- Never blend sources into a composite; preserve provenance.
- Known traps: `metadata` is a SQLAlchemy reserved word; include zero-config files (`postcss.config.js`, `alembic/script.py.mako`); pin `bcrypt==4.0.1` for passlib if auth is added; Docker running before uvicorn; Railway Root Directory = `backend`.
- Light formatting in docs; confirm direction before implementation; honest pushback over hedged agreement.

---

## 9. Milestones
- **M1 — Spot board + freshness honesty.** Instruments, Twelve Data (FX) + CoinGecko (crypto) adapters, `latest_price`, lazy-refresh + advisory lock, per-number source/timestamp/realtime/market-state badges, charts. *DoD: every price on screen carries honest provenance and freshness.*
- **M2 — Watchlist, change windows, alerts.** Unified watchlist, 1h/24h/7d %, threshold + peg alerts (in-app + PWA push), FX quick-convert.
- **M3 — Descriptive intelligence.** Rolling correlation, realized-vol regime bands, liquidity/spread read, cross-source divergence, cross-asset regime read, anomaly alerts (`intel_snapshot` precompute).
- **M4 — (Stretch) Crypto volume-activity forecast.** New model, uncertainty bands, crypto-only, GH Actions batch. Descriptive, non-directional.
- **Cross-cutting:** PWA polish, offline last-known (stamped stale), simple auth (see open Qs).

---

## 10. Open Questions
1. **Auth model** — single-client token, PIN (RoundUp pattern), or open for v1? Likely a lightweight token to start.
2. **Crypto cross-check venue** — Coinbase (US-clean) vs Binance (deepest liquidity)? Default Coinbase; easy to add both.
3. **Refresh TTL** — 30s vs 60s default? Set *after* `feasibility_check.py` shows real source cadence.
4. **v1 vs later** — confirm all M2 features are v1, or trim (e.g., quick-convert → M3).
5. **Intelligence depth** — correlation/vol windows (30-day default?), and which panels are board-level vs per-instrument.
6. **DXY sourcing** — true DXY vs a USD-basket proxy if the feed doesn't expose DXY directly (verify in feasibility).

---

## Deliverables this session
- **SCOPE.md** (this file).
- **feasibility_check.py** — measures real latency (p50/p95) and timestamp staleness for Twelve Data (FX) and CoinGecko (crypto), plus a crypto cross-source divergence probe (CoinGecko vs Coinbase). **Run before any code**; commit results to STATUS.md, then set the refresh TTL and freshness-badge claims from real numbers.

---

*Next: CLAUDE.md (implementation prompts / guardrails) and STATUS.md (session handoff) once feasibility numbers are in.*
