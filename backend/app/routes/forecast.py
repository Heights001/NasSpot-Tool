from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.volume_forecast import (
    get_forecast_response,
    run_volume_forecast,
    seed_volume_history,
)

router = APIRouter()


@router.get("/forecast")
async def get_forecast(db: AsyncSession = Depends(get_db)):
    return await get_forecast_response(db)


@router.post("/forecast/seed", status_code=202)
async def seed_forecast(db: AsyncSession = Depends(get_db)):
    """Seed volume history and compute initial forecast. One-shot bootstrap."""
    await seed_volume_history(db)
    await run_volume_forecast(db)
    return {"status": "ok"}
