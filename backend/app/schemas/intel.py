from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class SnapshotSchema(BaseModel):
    instrument_id: int
    symbol: str
    computed_at: datetime
    sample_count: Optional[int]
    rv_30d: Optional[Decimal]
    rv_regime: Optional[str]
    z_score: Optional[Decimal]
    price_pctile_30d: Optional[Decimal]
    spread_bps: Optional[Decimal]

    model_config = {"from_attributes": True}


class CorrelationSchema(BaseModel):
    instrument_id_a: int
    instrument_id_b: int
    symbol_a: str
    symbol_b: str
    pearson_r: Optional[Decimal]
    sample_count: Optional[int]


class DivergenceSchema(BaseModel):
    instrument_id: int
    symbol: str
    price_coingecko: Decimal
    price_coinbase: Decimal
    gap_bps: Decimal


class IntelResponse(BaseModel):
    snapshots: dict[int, SnapshotSchema]
    correlations: list[CorrelationSchema]
    divergence: list[DivergenceSchema]
    computed_at: datetime
