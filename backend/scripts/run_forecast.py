#!/usr/bin/env python3
"""GH Actions entry point: seed hourly volume history and recompute 24h forecast.

Usage:
    cd backend && python scripts/run_forecast.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

# Allow running from repo root: python backend/scripts/run_forecast.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("run_forecast")


async def main() -> None:
    from app.database import SessionLocal
    from app.services.volume_forecast import seed_volume_history, run_volume_forecast

    async with SessionLocal() as db:
        logger.info("Seeding volume history...")
        await seed_volume_history(db)
        logger.info("Running seasonal quantile model...")
        await run_volume_forecast(db)
        logger.info("Forecast complete.")


if __name__ == "__main__":
    asyncio.run(main())
