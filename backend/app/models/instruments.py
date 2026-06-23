from sqlalchemy import Column, Integer, String, Boolean
from ..database import Base


class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    display_name = Column(String(50), nullable=False)
    asset_class = Column(String(10), nullable=False)  # 'fx' | 'crypto'
    quote_ccy = Column(String(10), nullable=False, default="USD")
    provider_symbol_twelvedata = Column(String(30))
    provider_symbol_coingecko = Column(String(50))
    display_precision = Column(Integer, nullable=False, default=5)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_peg_watch = Column(Boolean, nullable=False, default=False)
