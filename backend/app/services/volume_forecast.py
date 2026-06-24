from __future__ import annotations

import asyncio
import logging
import math
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy import select, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.instruments import Instrument
from ..models.volume import VolumeHistory, VolumeForecast

logger = logging.getLogger(__name__)

_SEED_SOURCE = "coingecko_hourly"
_MIN_ROWS_TO_SKIP_SEED = 600   # 30d * ~24h; skip if already dense
_FORECAST_HOURS = 24
_MIN_SAMPLES_FOR_BUCKET = 2    # need ≥ 2 points to compute a meaningful spread


def _quantile(data: list[float], q: float) -> float:
    """Linear-interpolation quantile on sorted data."""
    s = sorted(data)
    n = len(s)
    if n == 1:
        return s[0]
    idx = q * (n - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= n:
        return s[lo]
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


def _seasonal_quantiles(
    series: list[tuple[datetime, float]],
) -> dict[tuple[int, int], tuple[float, float, float]]:
    """Return {(hour, weekday): (p25, p50, p75)} from hourly volume series."""
    groups: dict[tuple[int, int], list[float]] = defaultdict(list)
    for ts, vol in series:
        if vol > 0:
            groups[(ts.hour, ts.weekday())].append(vol)

    result = {}
    for key, vols in groups.items():
        if len(vols) >= _MIN_SAMPLES_FOR_BUCKET:
            result[key] = (
                _quantile(vols, 0.25),
                _quantile(vols, 0.50),
                _quantile(vols, 0.75),
            )
    return result


async def seed_volume_history(db: AsyncSession) -> None:
    """Fetch 30d of hourly volume from CoinGecko and upsert into volume_history."""
    result = await db.execute(
        select(Instrument).where(
            Instrument.asset_class == "crypto",
            Instrument.provider_symbol_coingecko.isnot(None),
            Instrument.is_active == True,
        )
    )
    instruments = result.scalars().all()

    headers: dict[str, str] = {}
    if settings.coingecko_demo_key:
        headers["x-cg-demo-api-key"] = settings.coingecko_demo_key

    cutoff = datetime.now(timezone.utc) - timedelta(days=31)

    async with httpx.AsyncClient(timeout=30.0, base_url="https://api.coingecko.com", headers=headers) as client:
        for i, inst in enumerate(instruments):
            if i > 0:
                await asyncio.sleep(0.6)

            # Check existing density
            count_result = await db.execute(
                select(func.count()).select_from(VolumeHistory).where(
                    VolumeHistory.instrument_id == inst.id,
                    VolumeHistory.source == _SEED_SOURCE,
                    VolumeHistory.ts >= cutoff,
                )
            )
            count = count_result.scalar_one()
            if count >= _MIN_ROWS_TO_SKIP_SEED:
                logger.info("Volume history for %s already dense (%d rows), skipping", inst.symbol, count)
                continue

            try:
                resp = await client.get(
                    f"/api/v3/coins/{inst.provider_symbol_coingecko}/market_chart",
                    params={"vs_currency": "usd", "days": "30"},
                )
                resp.raise_for_status()
                total_volumes = resp.json().get("total_volumes", [])

                rows = [
                    {
                        "instrument_id": inst.id,
                        "ts": datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc),
                        "volume_usd": Decimal(str(round(vol, 2))),
                        "source": _SEED_SOURCE,
                    }
                    for ts_ms, vol in total_volumes
                    if vol is not None and vol > 0
                ]
                if not rows:
                    continue

                stmt = pg_insert(VolumeHistory).values(rows)
                stmt = stmt.on_conflict_do_nothing()
                await db.execute(stmt)
                await db.commit()
                logger.info("Upserted %d hourly volume rows for %s", len(rows), inst.symbol)

            except Exception as exc:
                logger.error("Failed to seed volume history for %s: %s", inst.symbol, exc)
                await db.rollback()


async def run_volume_forecast(db: AsyncSession) -> None:
    """Fit seasonal quantile model and write 24h forecast for all crypto instruments."""
    result = await db.execute(
        select(Instrument).where(
            Instrument.asset_class == "crypto",
            Instrument.provider_symbol_coingecko.isnot(None),
            Instrument.is_active == True,
        )
    )
    instruments = result.scalars().all()

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    cutoff = now - timedelta(days=31)

    for inst in instruments:
        try:
            hist_result = await db.execute(
                select(VolumeHistory.ts, VolumeHistory.volume_usd)
                .where(
                    VolumeHistory.instrument_id == inst.id,
                    VolumeHistory.source == _SEED_SOURCE,
                    VolumeHistory.ts >= cutoff,
                )
                .order_by(VolumeHistory.ts)
            )
            rows_raw = hist_result.all()
            if len(rows_raw) < 48:
                logger.warning("Insufficient volume history for %s (%d rows), skipping", inst.symbol, len(rows_raw))
                continue

            series = [(r.ts, float(r.volume_usd)) for r in rows_raw]
            qmap = _seasonal_quantiles(series)
            if not qmap:
                continue

            forecast_rows = []
            for h in range(1, _FORECAST_HOURS + 1):
                horizon_ts = now + timedelta(hours=h)
                key = (horizon_ts.hour, horizon_ts.weekday())
                if key not in qmap:
                    # Nearest available bucket (same hour, any weekday)
                    candidates = [(abs(k[1] - horizon_ts.weekday()), k) for k in qmap if k[0] == horizon_ts.hour]
                    if not candidates:
                        continue
                    _, key = min(candidates)
                p25, p50, p75 = qmap[key]
                forecast_rows.append({
                    "instrument_id": inst.id,
                    "generated_at": now,
                    "horizon_ts": horizon_ts,
                    "volume_p25": Decimal(str(round(p25, 2))),
                    "volume_p50": Decimal(str(round(p50, 2))),
                    "volume_p75": Decimal(str(round(p75, 2))),
                })

            if not forecast_rows:
                continue

            stmt = pg_insert(VolumeForecast).values(forecast_rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["instrument_id", "generated_at", "horizon_ts"],
                set_={
                    "volume_p25": stmt.excluded.volume_p25,
                    "volume_p50": stmt.excluded.volume_p50,
                    "volume_p75": stmt.excluded.volume_p75,
                },
            )
            await db.execute(stmt)
            await db.commit()
            logger.info("Wrote %d forecast rows for %s", len(forecast_rows), inst.symbol)

        except Exception as exc:
            logger.error("Failed to compute forecast for %s: %s", inst.symbol, exc)
            await db.rollback()


async def _short_term_vol(
    db: AsyncSession,
    instrument_ids: list[int],
) -> "dict[int, dict[int, float]]":
    """Avg volume-per-5min bar for the last 15m/30m/60m windows."""
    from ..models.intraday import PriceIntraday

    if not instrument_ids:
        return {}

    cutoff = datetime.now(timezone.utc) - timedelta(hours=26)
    result = await db.execute(
        select(PriceIntraday.instrument_id, PriceIntraday.volume)
        .where(
            PriceIntraday.instrument_id.in_(instrument_ids),
            PriceIntraday.ts >= cutoff,
            PriceIntraday.volume.isnot(None),
            PriceIntraday.volume > 0,
        )
        .order_by(PriceIntraday.instrument_id, PriceIntraday.ts.desc())
    )
    rows = result.all()

    by_inst: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        by_inst[r.instrument_id].append(float(r.volume))

    out: dict[int, dict[int, float]] = {}
    for iid, vols in by_inst.items():
        def avg(n: int) -> float:
            subset = vols[:n]
            return sum(subset) / len(subset) if subset else 0.0
        out[iid] = {15: round(avg(3), 4), 30: round(avg(6), 4), 60: round(avg(12), 4)}
    return out


async def get_forecast_response(db: AsyncSession) -> dict:
    """Return the latest 24h forecast for all crypto instruments."""
    # Latest generated_at per instrument
    latest_q = (
        select(
            VolumeForecast.instrument_id,
            func.max(VolumeForecast.generated_at).label("latest_gen"),
        )
        .group_by(VolumeForecast.instrument_id)
        .subquery()
    )

    # Join forecast rows to latest generation
    rows_result = await db.execute(
        select(
            VolumeForecast,
            Instrument.symbol,
        )
        .join(latest_q, (VolumeForecast.instrument_id == latest_q.c.instrument_id) & (VolumeForecast.generated_at == latest_q.c.latest_gen))
        .join(Instrument, Instrument.id == VolumeForecast.instrument_id)
        .order_by(VolumeForecast.instrument_id, VolumeForecast.horizon_ts)
    )
    all_rows = rows_result.all()

    if not all_rows:
        return {"generated_at": None, "instruments": {}}

    # Latest volume per instrument for activity badge
    latest_vol_q = (
        select(
            VolumeHistory.instrument_id,
            func.max(VolumeHistory.ts).label("latest_ts"),
        )
        .where(VolumeHistory.source == _SEED_SOURCE)
        .group_by(VolumeHistory.instrument_id)
        .subquery()
    )
    vol_result = await db.execute(
        select(VolumeHistory.instrument_id, VolumeHistory.volume_usd)
        .join(latest_vol_q, (VolumeHistory.instrument_id == latest_vol_q.c.instrument_id) & (VolumeHistory.ts == latest_vol_q.c.latest_ts))
    )
    latest_vols: dict[int, float] = {r.instrument_id: float(r.volume_usd) for r in vol_result}

    # Group forecast rows by instrument
    now = datetime.now(timezone.utc)
    by_inst: dict[int, dict] = {}
    generated_at: Optional[str] = None

    for row in all_rows:
        vf = row.VolumeForecast
        iid = vf.instrument_id
        if iid not in by_inst:
            by_inst[iid] = {
                "symbol": row.symbol,
                "current_volume": latest_vols.get(iid),
                "current_activity": None,
                "forecast": [],
            }
        if generated_at is None:
            generated_at = vf.generated_at.isoformat()

        by_inst[iid]["forecast"].append({
            "ts": vf.horizon_ts.isoformat(),
            "p25": float(vf.volume_p25),
            "p50": float(vf.volume_p50),
            "p75": float(vf.volume_p75),
        })

    # Compute activity badge using the first forecast slot closest to now
    for iid, inst_data in by_inst.items():
        current_vol = inst_data["current_volume"]
        if current_vol is None:
            continue
        # Find the nearest horizon slot
        nearest = min(inst_data["forecast"], key=lambda f: abs(datetime.fromisoformat(f["ts"]).replace(tzinfo=timezone.utc) - now), default=None)
        if nearest:
            p25, p75 = nearest["p25"], nearest["p75"]
            if current_vol >= p75:
                inst_data["current_activity"] = "busy"
            elif current_vol <= p25:
                inst_data["current_activity"] = "quiet"
            else:
                inst_data["current_activity"] = "typical"

    # Attach short-term vol (avg vol/bar) from intraday bars for crypto instruments
    crypto_ids = list(by_inst.keys())
    if crypto_ids:
        st = await _short_term_vol(db, crypto_ids)
        for iid in by_inst:
            sv = st.get(iid)
            by_inst[iid]["short_term_vol"] = (
                {"15": sv[15], "30": sv[30], "60": sv[60]} if sv else None
            )

    return {"generated_at": generated_at, "instruments": by_inst}
