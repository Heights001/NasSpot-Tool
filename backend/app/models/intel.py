from __future__ import annotations

from sqlalchemy import Column, Integer, ForeignKey, String, TIMESTAMP, Numeric
from ..database import Base


class IntelSnapshot(Base):
    __tablename__ = "intel_snapshot"

    instrument_id = Column(Integer, ForeignKey("instruments.id"), primary_key=True)
    computed_at = Column(TIMESTAMP(timezone=True), nullable=False)
    window_days = Column(Integer, nullable=False, default=30)
    sample_count = Column(Integer)
    rv_30d = Column(Numeric(8, 6))
    rv_regime = Column(String(10))
    price_mean_30d = Column(Numeric(20, 10))
    price_stdev_30d = Column(Numeric(20, 10))
    z_score = Column(Numeric(8, 4))
    price_pctile_30d = Column(Numeric(5, 2))
    spread_bps = Column(Numeric(10, 4))


class IntelCorrelation(Base):
    __tablename__ = "intel_correlation"

    instrument_id_a = Column(Integer, ForeignKey("instruments.id"), primary_key=True)
    instrument_id_b = Column(Integer, ForeignKey("instruments.id"), primary_key=True)
    computed_at = Column(TIMESTAMP(timezone=True), nullable=False)
    window_days = Column(Integer, nullable=False, default=30)
    pearson_r = Column(Numeric(6, 4))
    sample_count = Column(Integer)
