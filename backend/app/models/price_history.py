from sqlalchemy import Column, Integer, ForeignKey, String, TIMESTAMP, Numeric, Index
from ..database import Base


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    ts = Column(TIMESTAMP(timezone=True), nullable=False)
    price = Column(Numeric(20, 10), nullable=False)
    source = Column(String(50), nullable=False)

    __table_args__ = (
        Index("ix_price_history_instrument_ts", "instrument_id", "ts"),
    )
