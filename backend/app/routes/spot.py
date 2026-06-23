from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.instruments import Instrument
from ..models.latest_price import LatestPrice
from ..schemas.spot import FreshnessInfo, SpotBoardResponse, SpotPrice
from ..services.lazy_refresh import get_board_prices, get_or_refresh

router = APIRouter(prefix="/spot", tags=["spot"])


def _build_spot_price(instrument: Instrument, lp: Optional[LatestPrice], now: datetime) -> SpotPrice:
    freshness = None
    price = None
    if lp is not None:
        price = lp.price
        age = (now - lp.fetched_at).total_seconds() if lp.fetched_at else None
        freshness = FreshnessInfo(
            source=lp.source,
            source_ts=lp.source_ts,
            fetched_at=lp.fetched_at,
            is_realtime=lp.is_realtime,
            market_state=lp.market_state,
            age_seconds=age,
        )

    return SpotPrice(
        instrument_id=instrument.id,
        symbol=instrument.symbol,
        display_name=instrument.display_name,
        asset_class=instrument.asset_class,
        price=price,
        bid=lp.bid if lp else None,
        ask=lp.ask if lp else None,
        display_precision=instrument.display_precision,
        is_peg_watch=instrument.is_peg_watch,
        change_1h=lp.change_1h if lp else None,
        change_24h=lp.change_24h if lp else None,
        change_7d=lp.change_7d if lp else None,
        freshness=freshness,
    )


@router.get("", response_model=SpotBoardResponse)
async def get_board(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Instrument).where(Instrument.is_active == True).order_by(Instrument.sort_order)
    )
    instruments = result.scalars().all()

    prices = await get_board_prices(instruments, db)

    fx_prices: list[SpotPrice] = []
    crypto_prices: list[SpotPrice] = []

    for inst in instruments:
        spot = _build_spot_price(inst, prices.get(inst.id), now)
        if inst.asset_class == "fx":
            fx_prices.append(spot)
        else:
            crypto_prices.append(spot)

    return SpotBoardResponse(fx=fx_prices, crypto=crypto_prices, board_ts=now)


@router.get("/{symbol}", response_model=SpotPrice)
async def get_one(symbol: str, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Instrument).where(
            Instrument.symbol == symbol.upper(),
            Instrument.is_active == True,
        )
    )
    instrument = result.scalar_one_or_none()
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol!r} not found")

    lp = await get_or_refresh(instrument, db)
    return _build_spot_price(instrument, lp, now)
