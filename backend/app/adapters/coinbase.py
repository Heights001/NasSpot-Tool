from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.coinbase.com"

_CG_TO_CB: dict[str, str] = {
    "bitcoin": "BTC-USD",
    "ethereum": "ETH-USD",
    "solana": "SOL-USD",
    "ripple": "XRP-USD",
}


async def fetch_coinbase_prices(cg_ids: list[str]) -> dict[str, Decimal]:
    """Return {cg_id: price} for ids that have a Coinbase mapping. Never raises."""
    results: dict[str, Decimal] = {}
    async with httpx.AsyncClient(timeout=8.0, base_url=_BASE_URL) as client:
        for cg_id in cg_ids:
            product = _CG_TO_CB.get(cg_id)
            if not product:
                continue
            try:
                resp = await client.get(f"/v2/prices/{product}/spot")
                resp.raise_for_status()
                data = resp.json()
                amount = data.get("data", {}).get("amount")
                if amount:
                    results[cg_id] = Decimal(str(amount))
            except Exception as exc:
                logger.warning("Coinbase fetch failed for %s: %s", product, exc)
    return results
