from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx

from ..config import settings
from .base import BaseAdapter, QuoteResult

_SOURCE = "coingecko"
_BASE_URL = "https://api.coingecko.com"


class CoinGeckoAdapter(BaseAdapter):
    """Fetches crypto via /coins/markets — includes 1h/24h/7d % change."""

    def __init__(self) -> None:
        headers = {}
        if settings.coingecko_demo_key:
            headers["x-cg-demo-api-key"] = settings.coingecko_demo_key
        self._client = httpx.AsyncClient(timeout=10.0, base_url=_BASE_URL, headers=headers)

    async def fetch(self, symbols: list[str]) -> dict[str, QuoteResult]:
        """symbols are CoinGecko coin IDs (e.g. 'bitcoin', 'ethereum')."""
        if not symbols:
            return {}

        try:
            resp = await self._client.get(
                "/api/v3/coins/markets",
                params={
                    "ids": ",".join(symbols),
                    "vs_currency": "usd",
                    "price_change_percentage": "1h,24h,7d",
                    "sparkline": "false",
                },
            )
            resp.raise_for_status()
            data: list[dict] = resp.json()
        except Exception as exc:
            err = str(exc)
            return {
                sym: QuoteResult(
                    symbol=sym, price=Decimal(0), bid=None, ask=None,
                    source=_SOURCE, source_ts=None, is_realtime=False, error=err,
                )
                for sym in symbols
            }

        by_id = {row["id"]: row for row in data}

        results: dict[str, QuoteResult] = {}
        for cid in symbols:
            row = by_id.get(cid)
            if not row:
                results[cid] = QuoteResult(
                    symbol=cid, price=Decimal(0), bid=None, ask=None,
                    source=_SOURCE, source_ts=None, is_realtime=False,
                    error="id missing in response",
                )
                continue

            price = _safe_decimal(row.get("current_price"))
            if price is None:
                results[cid] = QuoteResult(
                    symbol=cid, price=Decimal(0), bid=None, ask=None,
                    source=_SOURCE, source_ts=None, is_realtime=False, error="bad price",
                )
                continue

            results[cid] = QuoteResult(
                symbol=cid,
                price=price,
                bid=None,
                ask=None,
                source=_SOURCE,
                source_ts=_parse_iso_ts(row.get("last_updated")),
                is_realtime=True,
                change_1h=_safe_decimal(row.get("price_change_percentage_1h_in_currency")),
                change_24h=_safe_decimal(row.get("price_change_percentage_24h_in_currency")),
                change_7d=_safe_decimal(row.get("price_change_percentage_7d_in_currency")),
            )

        return results

    async def close(self) -> None:
        await self._client.aclose()


def _safe_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _parse_iso_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
