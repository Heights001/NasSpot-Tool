from sqlalchemy import Column, Integer, ForeignKey, String, TIMESTAMP, Numeric, UniqueConstraint
from ..database import Base


class SourceQuote(Base):
    __tablename__ = "source_quote"

    id = Column(Integer, primary_key=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    source = Column(String(50), nullable=False)
    price = Column(Numeric(20, 10), nullable=False)
    source_ts = Column(TIMESTAMP(timezone=True))
    fetched_at = Column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("instrument_id", "source", name="uq_source_quote_instrument_source"),
    )
