from __future__ import annotations

from sqlalchemy import Column, Integer, ForeignKey, Numeric, TIMESTAMP
from ..database import Base


class PriceIntraday(Base):
    __tablename__ = "price_intraday"

    instrument_id = Column(Integer, ForeignKey("instruments.id"), primary_key=True)
    ts = Column(TIMESTAMP(timezone=True), primary_key=True)
    open  = Column(Numeric(20, 8), nullable=False)
    high  = Column(Numeric(20, 8), nullable=False)
    low   = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(24, 4))
