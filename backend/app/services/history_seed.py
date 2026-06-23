from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.instruments import Instrument
from ..models.price_history import PriceHistory

logger = logging.getLogger(__name__)

_TD_TO_YAHOO: dict[str, str] = {
    "EUR/USD": "EURUSD=X",
    "USD/JPY": "USDJPY=X",
    "GBP/USD": "GBPUSD=X",
    "USD/CHF": "USDCHF=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "USDCAD=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "USD/CNH": "USDCNH=X",
    "USD/MXN": "USDMXN=X",
    "USD/ZAR": "USDZAR=X",
    "USD/SGD": "USDSGD=X",
}

_CUTOFF_DAYS = 31


async def _count_hist_rows(db: AsyncSession, inst_id: int, source: str) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=_CUTOFF_DAYS)
    result = await db.execute(
        select(func.count()).select_from(PriceHistory).where(
            PriceHistory.instrument_id == inst_id,
            PriceHistory.source == source,
            PriceHistory.ts >= cutoff,
        )
    )
    return result.scalar_one()


async def seed_crypto_history(db: AsyncSession) -> None:
    """Seed 30d daily price history for all active crypto instruments from CoinGecko."""
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

    # Fetch all HTTP data outside the DB session sleep to avoid connection pool issues
    fetched: list[tuple[Instrument, list[dict]]] = []
    async with httpx.AsyncClient(timeout=15.0, base_url="https://api.coingecko.com", headers=headers) as client:
        for i, inst in enumerate(instruments):
            if i > 0:
                await asyncio.sleep(0.5)
            try:
                count = await _count_hist_rows(db, inst.id, "coingecko_hist")
                if count >= 25:
                    logger.info("Crypto %s already seeded (%d rows), skipping", inst.symbol, count)
                    continue

                resp = await client.get(
                    f"/api/v3/coins/{inst.provider_symbol_coingecko}/market_chart",
                    params={"vs_currency": "usd", "days": "30", "interval": "daily"},
                )
                resp.raise_for_status()
                price_points = resp.json().get("prices", [])

                rows = [
                    {
                        "instrument_id": inst.id,
                        "ts": datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc),
                        "price": Decimal(str(price)),
                        "source": "coingecko_hist",
                    }
                    for ts_ms, price in price_points
                    if price is not None
                ]
                fetched.append((inst, rows))
            except Exception as exc:
                logger.error("Failed to fetch crypto history for %s: %s", inst.symbol, exc)

    # Batch insert all at once
    for inst, rows in fetched:
        if not rows:
            continue
        try:
            await db.execute(pg_insert(PriceHistory).values(rows))
            await db.commit()
            logger.info("Seeded %d daily rows for crypto %s", len(rows), inst.symbol)
        except Exception as exc:
            logger.error("Failed to insert crypto history for %s: %s", inst.symbol, exc)
            await db.rollback()


async def seed_fx_history(db: AsyncSession) -> None:
    """Seed 30d daily price history for FX instruments from Yahoo Finance."""
    result = await db.execute(
        select(Instrument).where(
            Instrument.asset_class == "fx",
            Instrument.is_active == True,
        )
    )
    instruments = result.scalars().all()

    fetched: list[tuple[Instrument, list[dict]]] = []
    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
        for i, inst in enumerate(instruments):
            if i > 0:
                await asyncio.sleep(0.3)

            td_sym = inst.provider_symbol_twelvedata
            yahoo_sym = _TD_TO_YAHOO.get(td_sym or "")
            if not yahoo_sym:
                logger.warning("No Yahoo symbol for FX %s, skipping", inst.symbol)
                continue

            try:
                count = await _count_hist_rows(db, inst.id, "yahoo_hist")
                if count >= 20:
                    logger.info("FX %s already seeded (%d rows), skipping", inst.symbol, count)
                    continue

                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}"
                resp = await client.get(url, params={"interval": "1d", "range": "30d"})
                resp.raise_for_status()
                data = resp.json()

                result_data = data.get("chart", {}).get("result") or []
                if not result_data:
                    logger.warning("No Yahoo data for %s", yahoo_sym)
                    continue

                timestamps = result_data[0].get("timestamp", [])
                closes = (
                    result_data[0]
                    .get("indicators", {})
                    .get("quote", [{}])[0]
                    .get("close", [])
                )

                rows = [
                    {
                        "instrument_id": inst.id,
                        "ts": datetime.fromtimestamp(ts_unix, tz=timezone.utc),
                        "price": Decimal(str(close)),
                        "source": "yahoo_hist",
                    }
                    for ts_unix, close in zip(timestamps, closes)
                    if close is not None
                ]
                fetched.append((inst, rows))
            except Exception as exc:
                logger.error("Failed to fetch FX history for %s: %s", inst.symbol, exc)

    for inst, rows in fetched:
        if not rows:
            continue
        try:
            await db.execute(pg_insert(PriceHistory).values(rows))
            await db.commit()
            logger.info("Seeded %d daily rows for FX %s", len(rows), inst.symbol)
        except Exception as exc:
            logger.error("Failed to insert FX history for %s: %s", inst.symbol, exc)
            await db.rollback()
