from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.instruments import Instrument
from ..schemas.intel import IntelResponse
from ..services.history_seed import seed_crypto_history, seed_fx_history
from ..services.intel import get_intel_response

router = APIRouter(prefix="/intel", tags=["intel"])


async def _get_active_instruments(db: AsyncSession) -> list[Instrument]:
    result = await db.execute(
        select(Instrument).where(Instrument.is_active == True).order_by(Instrument.sort_order)
    )
    return list(result.scalars().all())


@router.get("", response_model=IntelResponse)
async def get_intel(db: AsyncSession = Depends(get_db)):
    instruments = await _get_active_instruments(db)
    data = await get_intel_response(instruments, db)
    return data


@router.post("/seed", status_code=202)
async def seed_history(db: AsyncSession = Depends(get_db)):
    await seed_crypto_history(db)
    await seed_fx_history(db)
    return {"message": "Seeding complete"}
