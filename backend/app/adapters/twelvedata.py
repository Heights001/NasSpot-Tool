import asyncio
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

import httpx

from ..config import settings
from .base import BaseAdapter, QuoteResult

_SOURCE = "twelvedata"
_BASE_URL = "https://api.twelvedata.com"
_BATCH_SIZE = 8  # free plan: up to 8 symbols per request


class TwelveDataAdapter(BaseAdapter):
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=15.0, base_url=_BASE_URL)

    async def fetch(self, symbols: list[str]) -> dict[str, QuoteResult]:
        if not symbols:
            return {}
        results: dict[str, QuoteResult] = {}
        batches = [symbols[i:i + _BATCH_SIZE] for i in range(0, len(symbols), _BATCH_SIZE)]
        for i, batch in enumerate(batches):
            if i > 0:
                await asyncio.sleep(1.5)  # stay within 8 req/min free-plan limit
            batch_results = await self._fetch_batch(batch)
            results.update(batch_results)
        return results

    async def _fetch_batch(self, symbols: list[str]) -> dict[str, QuoteResult]:
        try:
            resp = await self._client.get(
                "/quote",
                params={"symbol": ",".join(symbols), "apikey": settings.twelvedata_api_key},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            err = str(exc)
            return {s: QuoteResult(symbol=s, price=Decimal(0), bid=None, ask=None,
                                   source=_SOURCE, source_ts=None, is_realtime=False, error=err)
                    for s in symbols}

        # Multi-symbol response is {symbol: {...}, ...}; single-symbol is {...} directly
        if len(symbols) == 1:
            data = {symbols[0]: data}

        results: dict[str, QuoteResult] = {}
        for symbol in symbols:
            row = data.get(symbol, {})
            if isinstance(row, dict) and row.get("status") == "error":
                results[symbol] = QuoteResult(
                    symbol=symbol, price=Decimal(0), bid=None, ask=None,
                    source=_SOURCE, source_ts=None, is_realtime=False,
                    error=str(row.get("message", "twelvedata error")),
                )
                continue

            price = _safe_decimal((row.get("close") or row.get("price")) if isinstance(row, dict) else None)
            if price is None:
                results[symbol] = QuoteResult(
                    symbol=symbol, price=Decimal(0), bid=None, ask=None,
                    source=_SOURCE, source_ts=None, is_realtime=False, error="no price in response",
                )
                continue

            results[symbol] = QuoteResult(
                symbol=symbol,
                price=price,
                bid=_safe_decimal(row.get("bid") if isinstance(row, dict) else None),
                ask=_safe_decimal(row.get("ask") if isinstance(row, dict) else None),
                source=_SOURCE,
                source_ts=_parse_unix_ts(row.get("timestamp") if isinstance(row, dict) else None),
                is_realtime=True,
                change_24h=_safe_decimal(row.get("percent_change") if isinstance(row, dict) else None),
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


def _parse_unix_ts(ts) -> Optional[datetime]:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None
