from __future__ import annotations

from sqlalchemy import Integer, Numeric, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class VolumeHistory(Base):
    __tablename__ = "volume_history"

    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instruments.id"), primary_key=True)
    ts: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), primary_key=True)
    volume_usd: Mapped[object] = mapped_column(Numeric(24, 2), nullable=False)
    source: Mapped[str] = mapped_column(String(50), primary_key=True)


class VolumeForecast(Base):
    __tablename__ = "volume_forecast"

    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instruments.id"), primary_key=True)
    generated_at: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), primary_key=True)
    horizon_ts: Mapped[object] = mapped_column(TIMESTAMP(timezone=True), primary_key=True)
    volume_p25: Mapped[object] = mapped_column(Numeric(24, 2), nullable=False)
    volume_p50: Mapped[object] = mapped_column(Numeric(24, 2), nullable=False)
    volume_p75: Mapped[object] = mapped_column(Numeric(24, 2), nullable=False)
