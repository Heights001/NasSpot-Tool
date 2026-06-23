from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class QuoteResult:
    symbol: str
    price: Decimal
    bid: Optional[Decimal]
    ask: Optional[Decimal]
    source: str
    source_ts: Optional[datetime]
    is_realtime: bool
    error: Optional[str] = None
    change_1h: Optional[Decimal] = None
    change_24h: Optional[Decimal] = None
    change_7d: Optional[Decimal] = None

    @property
    def ok(self) -> bool:
        return self.error is None


class BaseAdapter(ABC):
    @abstractmethod
    async def fetch(self, symbols: list[str]) -> dict[str, QuoteResult]:
        """Fetch quotes for the given symbols. Returns symbol -> QuoteResult.
        Must never raise — return QuoteResult with error set on failure."""
        ...
