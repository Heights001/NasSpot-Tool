"""GH Actions entry point: seed intraday bars + retrain ML models."""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.database import SessionLocal
from app.services.intraday import seed_all_intraday
from app.services.ml_signals import train_all_models


async def main():
    async with SessionLocal() as db:
        print("=== Seeding intraday bars ===")
        seed_result = await seed_all_intraday(db, force=False)
        for inst_id, n in seed_result.items():
            print(f"  inst {inst_id}: {n} bars")

        print("=== Training ML models ===")
        train_result = await train_all_models(db)
        for inst_id, horizons in train_result.items():
            if isinstance(horizons, dict) and "error" in horizons:
                print(f"  inst {inst_id}: ERROR {horizons}")
            else:
                for h, info in horizons.items():
                    print(f"  inst {inst_id} +{h}m: acc={info.get('acc')} n={info.get('n')}")

    print("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
