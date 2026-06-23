from sqlalchemy import Column, Integer, ForeignKey, String, Boolean, TIMESTAMP, Numeric
from sqlalchemy.orm import relationship
from ..database import Base


class LatestPrice(Base):
    __tablename__ = "latest_price"

    instrument_id = Column(Integer, ForeignKey("instruments.id"), primary_key=True)
    price = Column(Numeric(20, 10), nullable=False)
    bid = Column(Numeric(20, 10))
    ask = Column(Numeric(20, 10))
    source = Column(String(50), nullable=False)
    source_ts = Column(TIMESTAMP(timezone=True))
    fetched_at = Column(TIMESTAMP(timezone=True), nullable=False)
    is_realtime = Column(Boolean, nullable=False, default=False)
    market_state = Column(String(20), nullable=False, default="open")
    change_1h = Column(Numeric(20, 10))
    change_24h = Column(Numeric(20, 10))
    change_7d = Column(Numeric(20, 10))

    instrument = relationship("Instrument", foreign_keys=[instrument_id])
