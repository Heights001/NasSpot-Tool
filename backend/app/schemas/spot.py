from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class FreshnessInfo(BaseModel):
    source: str
    source_ts: Optional[datetime]
    fetched_at: datetime
    is_realtime: bool
    market_state: str  # 'open' | 'closed' | 'weekend_gap'
    age_seconds: Optional[float]


class SpotPrice(BaseModel):
    instrument_id: int
    symbol: str
    display_name: str
    asset_class: str
    price: Optional[Decimal]
    bid: Optional[Decimal]
    ask: Optional[Decimal]
    display_precision: int
    is_peg_watch: bool
    change_1h: Optional[Decimal]
    change_24h: Optional[Decimal]
    change_7d: Optional[Decimal]
    freshness: Optional[FreshnessInfo]

    model_config = {"from_attributes": True}


class SpotBoardResponse(BaseModel):
    fx: list[SpotPrice]
    crypto: list[SpotPrice]
    board_ts: datetime
