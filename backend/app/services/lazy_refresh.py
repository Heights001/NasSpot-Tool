from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.base import QuoteResult
from ..adapters.coingecko import CoinGeckoAdapter
from ..adapters.twelvedata import TwelveDataAdapter
from ..config import settings
from ..models.instruments import Instrument
from ..models.latest_price import LatestPrice
from ..models.price_history import PriceHistory
from ..models.source_quote import SourceQuote
from ..services.market_state import MarketState, get_crypto_market_state, get_fx_market_state

_fx_adapter: TwelveDataAdapter | None = None
_cg_adapter: CoinGeckoAdapter | None = None


def _get_fx_adapter() -> TwelveDataAdapter:
    global _fx_adapter
    if _fx_adapter is None:
        _fx_adapter = TwelveDataAdapter()
    return _fx_adapter


def _get_cg_adapter() -> CoinGeckoAdapter:
    global _cg_adapter
    if _cg_adapter is None:
        _cg_adapter = CoinGeckoAdapter()
    return _cg_adapter


async def get_board_prices(
    instruments: list[Instrument], db: AsyncSession
) -> dict[int, LatestPrice | None]:
    """
    Batch refresh for the full board. One upstream call per provider, one commit total.
    Returns mapping of instrument_id → LatestPrice (None if never fetched).
    """
    now = datetime.now(timezone.utc)
    fx_market_state = get_fx_market_state(now)
    crypto_market_state = get_crypto_market_state()

    # Single query for all cached prices
    inst_ids = [i.id for i in instruments]
    result = await db.execute(
        select(LatestPrice).where(LatestPrice.instrument_id.in_(inst_ids))
    )
    cached: dict[int, LatestPrice] = {lp.instrument_id: lp for lp in result.scalars()}

    # Identify stale instruments per provider
    stale_crypto: list[Instrument] = []
    stale_fx: list[Instrument] = []
    for inst in instruments:
        row = cached.get(inst.id)
        if inst.asset_class == "crypto":
            ms, ttl = crypto_market_state, settings.crypto_ttl_seconds
        else:
            ms, ttl = fx_market_state, settings.fx_ttl_seconds
        if (row is None or (now - row.fetched_at).total_seconds() >= ttl) and ms == MarketState.OPEN:
            if inst.asset_class == "crypto" and inst.provider_symbol_coingecko:
                stale_crypto.append(inst)
            elif inst.asset_class == "fx" and inst.provider_symbol_twelvedata:
                stale_fx.append(inst)

    # Fetch from upstream (one HTTP call per provider)
    cg_quotes: dict[str, QuoteResult] = {}
    td_quotes: dict[str, QuoteResult] = {}
    if stale_crypto:
        try:
            cg_quotes = await _get_cg_adapter().fetch([i.provider_symbol_coingecko for i in stale_crypto])
        except Exception:
            pass
    if stale_fx:
        try:
            td_quotes = await _get_fx_adapter().fetch([i.provider_symbol_twelvedata for i in stale_fx])
        except Exception:
            pass

    # Collect writes — one batch upsert + one commit for all instruments
    lp_rows: list[dict] = []
    ph_rows: list[dict] = []
    sq_rows: list[dict] = []
    refreshed_ids: set[int] = set()

    for inst in stale_crypto:
        quote = cg_quotes.get(inst.provider_symbol_coingecko)
        if quote and quote.ok:
            lp_rows.append(_lp_dict(inst.id, quote, crypto_market_state, now))
            ph_rows.append({"instrument_id": inst.id, "ts": now, "price": quote.price, "source": quote.source})
            sq_rows.append(_sq_dict(inst.id, quote, now))
            refreshed_ids.add(inst.id)

    for inst in stale_fx:
        quote = td_quotes.get(inst.provider_symbol_twelvedata)
        if quote and quote.ok:
            lp_rows.append(_lp_dict(inst.id, quote, fx_market_state, now))
            ph_rows.append({"instrument_id": inst.id, "ts": now, "price": quote.price, "source": quote.source})
            sq_rows.append(_sq_dict(inst.id, quote, now))
            refreshed_ids.add(inst.id)

    if lp_rows:
        _lp_ins = pg_insert(LatestPrice).values(lp_rows)
        lp_upsert = _lp_ins.on_conflict_do_update(
            index_elements=["instrument_id"],
            set_={c: _lp_ins.excluded[c]
                  for c in ("price", "bid", "ask", "source", "source_ts",
                             "fetched_at", "is_realtime", "market_state",
                             "change_1h", "change_24h", "change_7d")},
        )
        _sq_ins = pg_insert(SourceQuote).values(sq_rows)
        sq_upsert = _sq_ins.on_conflict_do_update(
            constraint="uq_source_quote_instrument_source",
            set_={c: _sq_ins.excluded[c] for c in ("price", "source_ts", "fetched_at")},
        )
        await db.execute(lp_upsert)
        await db.execute(pg_insert(PriceHistory).values(ph_rows))
        await db.execute(sq_upsert)
        await db.commit()

        # Update cache in-memory — we have all the data already
        for row in lp_rows:
            cached[row["instrument_id"]] = LatestPrice(**row)

    # Apply market_state badge to non-refreshed stale rows
    out: dict[int, LatestPrice | None] = {}
    for inst in instruments:
        row = cached.get(inst.id)
        ms = crypto_market_state if inst.asset_class == "crypto" else fx_market_state
        if row is not None and ms != MarketState.OPEN and inst.id not in refreshed_ids:
            row.market_state = ms.value
        out[inst.id] = row
    return out


def _lp_dict(instrument_id: int, quote: QuoteResult, ms: MarketState, now: datetime) -> dict:
    return {
        "instrument_id": instrument_id,
        "price": quote.price,
        "bid": quote.bid,
        "ask": quote.ask,
        "source": quote.source,
        "source_ts": quote.source_ts,
        "fetched_at": now,
        "is_realtime": quote.is_realtime,
        "market_state": ms.value,
        "change_1h": quote.change_1h,
        "change_24h": quote.change_24h,
        "change_7d": quote.change_7d,
    }


def _sq_dict(instrument_id: int, quote: QuoteResult, now: datetime) -> dict:
    return {
        "instrument_id": instrument_id,
        "source": quote.source,
        "price": quote.price,
        "source_ts": quote.source_ts,
        "fetched_at": now,
    }


async def get_or_refresh(instrument: Instrument, db: AsyncSession) -> LatestPrice | None:
    """
    Return the latest price for an instrument, refreshing from upstream if stale.
    Never raises — returns None only if no data has ever been fetched.
    """
    result = await db.execute(
        select(LatestPrice).where(LatestPrice.instrument_id == instrument.id)
    )
    row = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    ttl = settings.crypto_ttl_seconds if instrument.asset_class == "crypto" else settings.fx_ttl_seconds
    market_state = (
        get_crypto_market_state()
        if instrument.asset_class == "crypto"
        else get_fx_market_state(now)
    )

    needs_refresh = (
        row is None or (now - row.fetched_at).total_seconds() >= ttl
    ) and market_state == MarketState.OPEN

    if not needs_refresh:
        if row is not None and market_state != MarketState.OPEN:
            row.market_state = market_state.value
        return row

    # Single-flight via advisory lock (prevents thundering herd)
    lock_key = instrument.id
    try:
        await db.execute(text(f"SELECT pg_advisory_xact_lock({lock_key})"))
    except Exception:
        return row  # fail open

    # Re-check after acquiring lock — another coroutine may have refreshed
    result = await db.execute(
        select(LatestPrice).where(LatestPrice.instrument_id == instrument.id)
    )
    row = result.scalar_one_or_none()
    if row is not None and (now - row.fetched_at).total_seconds() < ttl:
        return row

    # Fetch from upstream
    quote = await _fetch_quote(instrument)
    if quote is None or not quote.ok:
        if row is not None:
            row.market_state = market_state.value
        return row  # fail open: serve stale

    updated_row = await _upsert_price(instrument, quote, market_state, db, now)
    return updated_row


async def _fetch_quote(instrument: Instrument) -> "QuoteResult | None":
    try:
        if instrument.asset_class == "fx":
            if not instrument.provider_symbol_twelvedata:
                return None
            adapter = _get_fx_adapter()
            results = await adapter.fetch([instrument.provider_symbol_twelvedata])
            return results.get(instrument.provider_symbol_twelvedata)
        else:
            if not instrument.provider_symbol_coingecko:
                return None
            adapter = _get_cg_adapter()
            results = await adapter.fetch([instrument.provider_symbol_coingecko])
            return results.get(instrument.provider_symbol_coingecko)
    except Exception:
        return None


async def _upsert_price(
    instrument: Instrument,
    quote: "QuoteResult",
    market_state: MarketState,
    db: AsyncSession,
    now: datetime,
) -> LatestPrice:
    stmt = pg_insert(LatestPrice).values(
        instrument_id=instrument.id,
        price=quote.price,
        bid=quote.bid,
        ask=quote.ask,
        source=quote.source,
        source_ts=quote.source_ts,
        fetched_at=now,
        is_realtime=quote.is_realtime,
        market_state=market_state.value,
    ).on_conflict_do_update(
        index_elements=["instrument_id"],
        set_={
            "price": quote.price,
            "bid": quote.bid,
            "ask": quote.ask,
            "source": quote.source,
            "source_ts": quote.source_ts,
            "fetched_at": now,
            "is_realtime": quote.is_realtime,
            "market_state": market_state.value,
        },
    )
    await db.execute(stmt)

    db.add(PriceHistory(
        instrument_id=instrument.id,
        ts=now,
        price=quote.price,
        source=quote.source,
    ))

    sq_stmt = pg_insert(SourceQuote).values(
        instrument_id=instrument.id,
        source=quote.source,
        price=quote.price,
        source_ts=quote.source_ts,
        fetched_at=now,
    ).on_conflict_do_update(
        constraint="uq_source_quote_instrument_source",
        set_={
            "price": quote.price,
            "source_ts": quote.source_ts,
            "fetched_at": now,
        },
    )
    await db.execute(sq_stmt)

    await db.commit()

    result = await db.execute(
        select(LatestPrice).where(LatestPrice.instrument_id == instrument.id)
    )
    return result.scalar_one()
