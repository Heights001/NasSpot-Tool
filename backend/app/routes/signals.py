from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.instruments import Instrument
from ..services.ml_signals import get_all_predictions, train_all_models
from ..services.intraday import seed_all_intraday

router = APIRouter(prefix="/signals", tags=["signals"])


async def _active_instruments(db: AsyncSession) -> list[Instrument]:
    r = await db.execute(
        select(Instrument).where(Instrument.is_active == True).order_by(Instrument.sort_order)
    )
    return list(r.scalars().all())


@router.get("")
async def get_signals(db: AsyncSession = Depends(get_db)):
    instruments = await _active_instruments(db)
    return await get_all_predictions(db, instruments)


@router.post("/train", status_code=202)
async def trigger_train(db: AsyncSession = Depends(get_db)):
    """Seed intraday bars + retrain all models. Can take 60–120s."""
    instruments = await _active_instruments(db)
    seed_result = await seed_all_intraday(db)
    train_result = await train_all_models(db)
    return {"seeded": seed_result, "trained": train_result}
