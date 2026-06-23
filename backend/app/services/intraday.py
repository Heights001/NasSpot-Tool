"""Seed 5-min OHLCV bars: Coinbase for crypto, yfinance for FX."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.instruments import Instrument
from ..models.intraday import PriceIntraday

logger = logging.getLogger(__name__)

# Coinbase product IDs for our crypto instruments
COINBASE_PRODUCTS: dict[int, str] = {
    16: "BTC-USD",
    18: "SOL-USD",
}

# yfinance tickers for our FX instruments
YF_TICKERS: dict[int, str] = {
    1: "EURUSD=X",
    2: "USDJPY=X",
    9: "EURJPY=X",
}

# USDT (id=21) is stable — no intraday ML, shows PEG status
_GRANULARITY_SECS = 300   # 5-min bars
_SEED_DAYS = 30
_MIN_ROWS_BEFORE_SKIP = 5000  # ~12 days at 5-min


async def _count_intraday(db: AsyncSession, instrument_id: int) -> int:
    r = await db.execute(
        text("SELECT COUNT(*) FROM price_intraday WHERE instrument_id = :id"),
        {"id": instrument_id},
    )
    return r.scalar() or 0


_CHUNK = 1000   # rows per INSERT (7 cols × 1000 = 7000 params, well under 32767)

async def _upsert_bars(db: AsyncSession, rows: list[dict]) -> None:
    if not rows:
        return
    for i in range(0, len(rows), _CHUNK):
        chunk = rows[i:i + _CHUNK]
        ins = pg_insert(PriceIntraday).values(chunk)
        stmt = ins.on_conflict_do_nothing(index_elements=["instrument_id", "ts"])
        await db.execute(stmt)


async def seed_coinbase(db: AsyncSession, instrument_id: int, product_id: str) -> int:
    """Fetch up to 30 days of 5-min candles from Coinbase public API."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=_SEED_DAYS)

    all_rows: list[dict] = []
    chunk_end = end
    chunk_secs = _GRANULARITY_SECS * 299  # 299 bars per request

    async with httpx.AsyncClient(timeout=20) as client:
        while chunk_end > start:
            chunk_start = max(chunk_end - timedelta(seconds=chunk_secs), start)
            try:
                resp = await client.get(
                    f"https://api.exchange.coinbase.com/products/{product_id}/candles",
                    params={
                        "granularity": _GRANULARITY_SECS,
                        "start": chunk_start.isoformat(),
                        "end": chunk_end.isoformat(),
                    },
                )
                resp.raise_for_status()
            except Exception as exc:
                logger.warning("Coinbase candles error %s: %s", product_id, exc)
                break

            candles = resp.json()
            if not candles:
                break

            for c in candles:
                ts_epoch, low, high, open_, close, volume = c
                ts = datetime.fromtimestamp(ts_epoch, tz=timezone.utc)
                all_rows.append({
                    "instrument_id": instrument_id,
                    "ts": ts,
                    "open": Decimal(str(open_)),
                    "high": Decimal(str(high)),
                    "low":  Decimal(str(low)),
                    "close": Decimal(str(close)),
                    "volume": Decimal(str(volume)),
                })

            chunk_end = chunk_start

    await _upsert_bars(db, all_rows)
    await db.commit()
    logger.info("Coinbase seeded %d bars for %s", len(all_rows), product_id)
    return len(all_rows)


async def seed_yfinance(db: AsyncSession, instrument_id: int, ticker_sym: str) -> int:
    """Fetch 5-min bars from yfinance (Yahoo Finance, no key needed)."""
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        logger.error("yfinance/pandas not installed — skipping %s", ticker_sym)
        return 0

    try:
        ticker = yf.Ticker(ticker_sym)
        # yfinance 5m interval available for last 60 days; use 30d
        hist = ticker.history(period="30d", interval="5m", auto_adjust=True)
    except Exception as exc:
        logger.warning("yfinance error %s: %s", ticker_sym, exc)
        return 0

    if hist is None or len(hist) == 0:
        return 0

    # Normalize index to UTC
    if hist.index.tzinfo is None:
        hist.index = hist.index.tz_localize("UTC")
    else:
        hist.index = hist.index.tz_convert("UTC")

    rows: list[dict] = []
    for ts, row in hist.iterrows():
        try:
            rows.append({
                "instrument_id": instrument_id,
                "ts": ts.to_pydatetime(),
                "open":  Decimal(str(round(float(row["Open"]), 8))),
                "high":  Decimal(str(round(float(row["High"]), 8))),
                "low":   Decimal(str(round(float(row["Low"]), 8))),
                "close": Decimal(str(round(float(row["Close"]), 8))),
                "volume": Decimal(str(int(row.get("Volume", 0) or 0))),
            })
        except Exception:
            continue

    await _upsert_bars(db, rows)
    await db.commit()
    logger.info("yfinance seeded %d bars for %s", len(rows), ticker_sym)
    return len(rows)


async def seed_all_intraday(db: AsyncSession, force: bool = False) -> dict[int, int]:
    """Seed all active instruments. Skips if already has enough bars (unless force=True)."""
    result: dict[int, int] = {}

    for inst_id, product_id in COINBASE_PRODUCTS.items():
        if not force:
            count = await _count_intraday(db, inst_id)
            if count >= _MIN_ROWS_BEFORE_SKIP:
                logger.info("Coinbase %s: %d bars already, skipping", product_id, count)
                result[inst_id] = count
                continue
        n = await seed_coinbase(db, inst_id, product_id)
        result[inst_id] = n

    for inst_id, ticker in YF_TICKERS.items():
        if not force:
            count = await _count_intraday(db, inst_id)
            if count >= _MIN_ROWS_BEFORE_SKIP:
                logger.info("yfinance %s: %d bars already, skipping", ticker, count)
                result[inst_id] = count
                continue
        n = await seed_yfinance(db, inst_id, ticker)
        result[inst_id] = n

    return result


async def get_recent_bars(
    db: AsyncSession, instrument_id: int, n_bars: int = 300
) -> list[tuple[datetime, float, float, float, float, float]]:
    """Return last n_bars of (ts, open, high, low, close, volume) ordered asc."""
    r = await db.execute(
        text("""
            SELECT ts, open, high, low, close, COALESCE(volume, 0)
            FROM price_intraday
            WHERE instrument_id = :id
            ORDER BY ts DESC
            LIMIT :n
        """),
        {"id": instrument_id, "n": n_bars},
    )
    rows = r.fetchall()
    # Return in ascending order (oldest first)
    return [(r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]))
            for r in reversed(rows)]
