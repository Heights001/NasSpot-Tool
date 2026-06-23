from __future__ import annotations

from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, TIMESTAMP, Text
from ..database import Base


class MLModelMeta(Base):
    __tablename__ = "ml_model_meta"

    instrument_id   = Column(Integer, ForeignKey("instruments.id"), primary_key=True)
    horizon_minutes = Column(Integer, primary_key=True)
    trained_at      = Column(TIMESTAMP(timezone=True), nullable=False)
    n_samples       = Column(Integer)
    cv_accuracy     = Column(Numeric(5, 4))
    feature_names_json = Column(Text)
    coef_json       = Column(Text)
    intercept       = Column(Numeric(12, 8))
    scaler_mean_json  = Column(Text)
    scaler_scale_json = Column(Text)


class MLPrediction(Base):
    __tablename__ = "ml_prediction"

    instrument_id   = Column(Integer, ForeignKey("instruments.id"), primary_key=True)
    horizon_minutes = Column(Integer, primary_key=True)
    predicted_at    = Column(TIMESTAMP(timezone=True), nullable=False)
    prob_up         = Column(Numeric(5, 4), nullable=False)
    signal          = Column(String(10), nullable=False)
    confidence      = Column(String(10), nullable=False)
