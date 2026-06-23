from __future__ import annotations

import math
import logging
import statistics
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.coinbase import fetch_coinbase_prices
from ..models.instruments import Instrument
from ..models.intel import IntelCorrelation, IntelSnapshot
from ..models.latest_price import LatestPrice
from . import ta as _ta

logger = logging.getLogger(__name__)

_INTEL_TTL_HOURS = 4


def _rv_regime(rv: float, asset_class: str) -> str:
    if asset_class == "crypto":
        if rv < 0.40:
            return "low"
        if rv < 0.80:
            return "normal"
        if rv < 1.20:
            return "high"
        return "extreme"
    else:
        if rv < 0.05:
            return "low"
        if rv < 0.10:
            return "normal"
        if rv < 0.20:
            return "high"
        return "extreme"


def _pearson(xs: list[float], ys: list[float]) -> Optional[float]:
    n = len(xs)
    if n < 5:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denom = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / denom if denom > 0 else None


async def refresh_intel(instruments: list[Instrument], db: AsyncSession) -> None:
    """Recompute intel_snapshot and intel_correlation if stale (> TTL)."""
    now = datetime.now(timezone.utc)
    inst_ids = [i.id for i in instruments]

    # Check freshness
    snap_result = await db.execute(
        select(IntelSnapshot).where(IntelSnapshot.instrument_id.in_(inst_ids))
    )
    existing = snap_result.scalars().all()
    if len(existing) == len(instruments) and all(
        (now - s.computed_at).total_seconds() < _INTEL_TTL_HOURS * 3600
        for s in existing
    ):
        return  # all fresh

    # Fetch all daily price series in one query
    rows = await db.execute(
        text("""
            SELECT instrument_id,
                   date_trunc('day', ts AT TIME ZONE 'UTC') AS day,
                   EXP(AVG(LN(price::float))) AS price
            FROM price_history
            WHERE instrument_id = ANY(:ids)
              AND ts >= now() - INTERVAL '31 days'
            GROUP BY 1, 2
            ORDER BY 1, 2
        """),
        {"ids": inst_ids},
    )
    series_raw = rows.fetchall()

    # Group by instrument_id -> list of (day, price)
    from collections import defaultdict
    series_by_id: dict[int, list[tuple]] = defaultdict(list)
    for inst_id, day, price in series_raw:
        series_by_id[inst_id].append((day, float(price)))

    # Fetch latest prices for current price + spread
    lp_result = await db.execute(
        select(LatestPrice).where(LatestPrice.instrument_id.in_(inst_ids))
    )
    latest_by_id: dict[int, LatestPrice] = {lp.instrument_id: lp for lp in lp_result.scalars()}

    inst_by_id = {i.id: i for i in instruments}

    snap_rows = []
    for inst_id in inst_ids:
        inst = inst_by_id[inst_id]
        lp = latest_by_id.get(inst_id)
        series = series_by_id.get(inst_id, [])
        prices = [p for (_, p) in series]

        if len(prices) < 5:
            snap_rows.append({
                "instrument_id": inst_id,
                "computed_at": now,
                "window_days": 30,
                "sample_count": len(prices),
                "rv_30d": None,
                "rv_regime": None,
                "price_mean_30d": None,
                "price_stdev_30d": None,
                "z_score": None,
                "price_pctile_30d": None,
                "spread_bps": _spread_bps(lp),
                "rsi_14": None,
                "bb_pct_b": None,
                "sma_trend": None,
                "ta_composite": None,
                "ta_reasoning": None,
            })
            continue

        # Log returns
        log_returns = [
            math.log(prices[i] / prices[i - 1])
            for i in range(1, len(prices))
            if prices[i - 1] > 0 and prices[i] > 0
        ]

        rv = None
        regime = None
        if len(log_returns) >= 5:
            rv = statistics.stdev(log_returns) * math.sqrt(365)
            regime = _rv_regime(rv, inst.asset_class)

        price_mean = statistics.mean(prices)
        price_stdev = statistics.stdev(prices) if len(prices) > 1 else None

        current = float(lp.price) if lp and lp.price else None
        z = None
        pctile = None
        if current is not None and price_stdev and price_stdev > 0:
            z = (current - price_mean) / price_stdev
            pctile = 100.0 * sum(1 for p in prices if p < current) / len(prices)

        rsi_val = _ta.rsi(prices)
        bb_val = _ta.bollinger_pct_b(prices)
        trend = _ta.sma_trend(prices)
        composite, reasoning = _ta.ta_composite(rsi_val, bb_val, trend, regime)

        snap_rows.append({
            "instrument_id": inst_id,
            "computed_at": now,
            "window_days": 30,
            "sample_count": len(prices),
            "rv_30d": Decimal(str(rv)) if rv is not None else None,
            "rv_regime": regime,
            "price_mean_30d": Decimal(str(price_mean)),
            "price_stdev_30d": Decimal(str(price_stdev)) if price_stdev is not None else None,
            "z_score": Decimal(str(round(z, 4))) if z is not None else None,
            "price_pctile_30d": Decimal(str(round(pctile, 2))) if pctile is not None else None,
            "spread_bps": _spread_bps(lp),
            "rsi_14": Decimal(str(rsi_val)) if rsi_val is not None else None,
            "bb_pct_b": Decimal(str(bb_val)) if bb_val is not None else None,
            "sma_trend": trend,
            "ta_composite": composite,
            "ta_reasoning": reasoning,
        })

    if snap_rows:
        ins = pg_insert(IntelSnapshot).values(snap_rows)
        upsert = ins.on_conflict_do_update(
            index_elements=["instrument_id"],
            set_={c: ins.excluded[c]
                  for c in ("computed_at", "window_days", "sample_count",
                             "rv_30d", "rv_regime", "price_mean_30d",
                             "price_stdev_30d", "z_score", "price_pctile_30d", "spread_bps",
                             "rsi_14", "bb_pct_b", "sma_trend", "ta_composite", "ta_reasoning")},
        )
        await db.execute(upsert)

    # Compute correlations — build daily log-return series per instrument
    ret_series: dict[int, dict] = {}  # inst_id -> {day: log_ret}
    for inst_id in inst_ids:
        series = series_by_id.get(inst_id, [])
        prices_map = {day: price for day, price in series}
        days_sorted = sorted(prices_map)
        log_rets = {}
        for i in range(1, len(days_sorted)):
            prev = prices_map[days_sorted[i - 1]]
            curr = prices_map[days_sorted[i]]
            if prev > 0 and curr > 0:
                log_rets[days_sorted[i]] = math.log(curr / prev)
        if len(log_rets) >= 5:
            ret_series[inst_id] = log_rets

    corr_rows = []
    ids_with_data = sorted(ret_series.keys())
    for i, id_a in enumerate(ids_with_data):
        for id_b in ids_with_data[i + 1:]:
            a_series = ret_series[id_a]
            b_series = ret_series[id_b]
            common_days = sorted(set(a_series) & set(b_series))
            if len(common_days) < 5:
                continue
            xs = [a_series[d] for d in common_days]
            ys = [b_series[d] for d in common_days]
            r = _pearson(xs, ys)
            if r is None:
                continue
            # Always store with smaller id first
            a_id, b_id = (id_a, id_b) if id_a < id_b else (id_b, id_a)
            corr_rows.append({
                "instrument_id_a": a_id,
                "instrument_id_b": b_id,
                "computed_at": now,
                "window_days": 30,
                "pearson_r": Decimal(str(round(r, 4))),
                "sample_count": len(common_days),
            })

    if corr_rows:
        c_ins = pg_insert(IntelCorrelation).values(corr_rows)
        c_upsert = c_ins.on_conflict_do_update(
            index_elements=["instrument_id_a", "instrument_id_b"],
            set_={c: c_ins.excluded[c]
                  for c in ("computed_at", "window_days", "pearson_r", "sample_count")},
        )
        await db.execute(c_upsert)

    await db.commit()
    logger.info("Intel refresh complete: %d snapshots, %d correlations", len(snap_rows), len(corr_rows))


def _spread_bps(lp: Optional[LatestPrice]) -> Optional[Decimal]:
    if not lp or not lp.bid or not lp.ask or not lp.price:
        return None
    try:
        bid = float(lp.bid)
        ask = float(lp.ask)
        mid = float(lp.price)
        if mid <= 0:
            return None
        return Decimal(str(round((ask - bid) / mid * 10000, 4)))
    except Exception:
        return None


async def get_intel_response(instruments: list[Instrument], db: AsyncSession) -> dict:
    """Return full intel response: snapshots, correlations, divergence."""
    await refresh_intel(instruments, db)

    inst_ids = [i.id for i in instruments]
    inst_by_id = {i.id: i for i in instruments}

    # Fetch snapshots
    snap_result = await db.execute(
        select(IntelSnapshot).where(IntelSnapshot.instrument_id.in_(inst_ids))
    )
    snapshots_by_id = {s.instrument_id: s for s in snap_result.scalars()}

    # Fetch correlations
    corr_result = await db.execute(
        select(IntelCorrelation).where(
            IntelCorrelation.instrument_id_a.in_(inst_ids),
            IntelCorrelation.instrument_id_b.in_(inst_ids),
        )
    )
    correlations = corr_result.scalars().all()

    # Coinbase divergence for crypto
    crypto_insts = [i for i in instruments if i.asset_class == "crypto" and i.provider_symbol_coingecko]
    cg_ids = [i.provider_symbol_coingecko for i in crypto_insts]
    cb_prices = await fetch_coinbase_prices(cg_ids)

    # Fetch latest prices for divergence comparison
    lp_result = await db.execute(
        select(LatestPrice).where(LatestPrice.instrument_id.in_(inst_ids))
    )
    lp_by_id = {lp.instrument_id: lp for lp in lp_result.scalars()}

    divergence = []
    for inst in crypto_insts:
        cb_price = cb_prices.get(inst.provider_symbol_coingecko)
        lp = lp_by_id.get(inst.id)
        if cb_price and lp and lp.price:
            cg_price = lp.price
            gap_bps = abs(float(cb_price) - float(cg_price)) / float(cg_price) * 10000
            divergence.append({
                "instrument_id": inst.id,
                "symbol": inst.symbol,
                "price_coingecko": cg_price,
                "price_coinbase": cb_price,
                "gap_bps": Decimal(str(round(gap_bps, 2))),
            })

    # Build snapshots dict with symbol
    snapshots_out = {}
    for inst_id, snap in snapshots_by_id.items():
        inst = inst_by_id.get(inst_id)
        snapshots_out[inst_id] = {
            "instrument_id": inst_id,
            "symbol": inst.symbol if inst else str(inst_id),
            "computed_at": snap.computed_at,
            "sample_count": snap.sample_count,
            "rv_30d": snap.rv_30d,
            "rv_regime": snap.rv_regime,
            "z_score": snap.z_score,
            "price_pctile_30d": snap.price_pctile_30d,
            "spread_bps": snap.spread_bps,
            "rsi_14": snap.rsi_14,
            "bb_pct_b": snap.bb_pct_b,
            "sma_trend": snap.sma_trend,
            "ta_composite": snap.ta_composite,
            "ta_reasoning": snap.ta_reasoning,
        }

    # Build correlations list with symbols
    corrs_out = []
    for c in correlations:
        inst_a = inst_by_id.get(c.instrument_id_a)
        inst_b = inst_by_id.get(c.instrument_id_b)
        corrs_out.append({
            "instrument_id_a": c.instrument_id_a,
            "instrument_id_b": c.instrument_id_b,
            "symbol_a": inst_a.symbol if inst_a else str(c.instrument_id_a),
            "symbol_b": inst_b.symbol if inst_b else str(c.instrument_id_b),
            "pearson_r": c.pearson_r,
            "sample_count": c.sample_count,
        })
    # Sort by |r| desc
    corrs_out.sort(key=lambda x: abs(float(x["pearson_r"])) if x["pearson_r"] else 0, reverse=True)

    return {
        "snapshots": snapshots_out,
        "correlations": corrs_out,
        "divergence": divergence,
        "computed_at": datetime.now(timezone.utc),
    }
