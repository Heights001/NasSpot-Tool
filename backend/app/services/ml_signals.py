"""ML price-direction model: LogisticRegression per (instrument, horizon)."""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.instruments import Instrument
from ..models.ml import MLModelMeta, MLPrediction
from .intraday import COINBASE_PRODUCTS, YF_TICKERS, get_recent_bars

logger = logging.getLogger(__name__)

HORIZONS = [15, 30, 60]            # minutes
BARS_PER_HORIZON = {15: 3, 30: 6, 60: 12}  # at 5-min bars
FEATURE_NAMES = [
    "rsi_14", "bb_pct_b", "momentum_1h", "momentum_4h",
    "volume_zscore", "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "regime_encoded",
]

# Instruments with ML (USDT is stable peg — skip)
ML_INSTRUMENT_IDS = list(COINBASE_PRODUCTS.keys()) + list(YF_TICKERS.keys())


# ── Pure-Python signal helpers ────────────────────────────────────────────────

def _rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(0.0, d))
        losses.append(max(0.0, -d))
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100.0
    return round(100.0 - 100.0 / (1 + ag / al), 4)


def _bb_pct_b(closes: list[float], period: int = 20, k: float = 2.0) -> Optional[float]:
    if len(closes) < period:
        return None
    w = closes[-period:]
    mean = sum(w) / period
    std = math.sqrt(sum((x - mean) ** 2 for x in w) / period)
    if std == 0:
        return None
    return round((closes[-1] - (mean - k * std)) / (2 * k * std), 4)


def _momentum(closes: list[float], n_bars: int) -> Optional[float]:
    if len(closes) < n_bars + 1:
        return None
    prev = closes[-(n_bars + 1)]
    if prev == 0:
        return None
    return (closes[-1] - prev) / prev


def _volume_zscore(volumes: list[float], window: int = 288) -> float:
    """Z-score of last volume relative to rolling window (288 bars = 24h)."""
    if len(volumes) < 2:
        return 0.0
    w = volumes[-window:]
    mean = sum(w) / len(w)
    std = math.sqrt(sum((x - mean) ** 2 for x in w) / len(w))
    if std == 0:
        return 0.0
    return (volumes[-1] - mean) / std


def _cyclical(value: float, period: float) -> tuple[float, float]:
    angle = 2 * math.pi * value / period
    return math.sin(angle), math.cos(angle)


def _regime_encoded(rv: Optional[float], asset_class: str) -> float:
    """Convert RV regime to 0–3 numeric."""
    if rv is None:
        return 1.0
    thresholds = {"fx": (0.04, 0.08, 0.15), "crypto": (0.40, 0.80, 1.50)}
    lo, mid, hi = thresholds.get(asset_class, (0.04, 0.08, 0.15))
    if rv < lo:
        return 0.0
    if rv < mid:
        return 1.0
    if rv < hi:
        return 2.0
    return 3.0


def _build_feature_vector(
    bars: list[tuple],  # (ts, open, high, low, close, volume)
    rv: Optional[float],
    asset_class: str,
) -> Optional[list[float]]:
    """Build a single feature vector from recent bars. Returns None if insufficient data."""
    if len(bars) < 50:
        return None

    closes  = [b[4] for b in bars]
    volumes = [b[5] for b in bars]
    ts: datetime = bars[-1][0]

    rsi = _rsi(closes)
    bb  = _bb_pct_b(closes)
    m1h = _momentum(closes, 12)   # 12 × 5min = 1hr
    m4h = _momentum(closes, 48)   # 48 × 5min = 4hr
    vsz = _volume_zscore(volumes)
    h_sin, h_cos = _cyclical(ts.hour + ts.minute / 60, 24)
    d_sin, d_cos = _cyclical(ts.weekday(), 7)
    reg = _regime_encoded(rv, asset_class)

    # Replace None with neutral defaults
    rsi = rsi if rsi is not None else 50.0
    bb  = bb  if bb  is not None else 0.5
    m1h = m1h if m1h is not None else 0.0
    m4h = m4h if m4h is not None else 0.0

    return [rsi, bb, m1h, m4h, vsz, h_sin, h_cos, d_sin, d_cos, reg]


# ── StandardScaler ─────────────────────────────────────────────────────────────

def _fit_scaler(X: list[list[float]]) -> tuple[list[float], list[float]]:
    n_feat = len(X[0])
    means = [sum(row[i] for row in X) / len(X) for i in range(n_feat)]
    scales = []
    for i in range(n_feat):
        var = sum((row[i] - means[i]) ** 2 for row in X) / len(X)
        scales.append(math.sqrt(var) or 1.0)
    return means, scales


def _apply_scaler(x: list[float], means: list[float], scales: list[float]) -> list[float]:
    return [(x[i] - means[i]) / scales[i] for i in range(len(x))]


# ── Logistic Regression ────────────────────────────────────────────────────────

def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def _lr_predict_proba(x: list[float], coef: list[float], intercept: float) -> float:
    z = intercept + sum(c * xi for c, xi in zip(coef, x))
    return _sigmoid(z)


def _train_lr(
    X: list[list[float]], y: list[int], lr: float = 0.1, epochs: int = 200
) -> tuple[list[float], float]:
    """Pure-Python logistic regression via gradient descent."""
    n_feat = len(X[0])
    n_samples = len(X)
    coef = [0.0] * n_feat
    intercept = 0.0

    for _ in range(epochs):
        grad_coef = [0.0] * n_feat
        grad_int  = 0.0
        for xi, yi in zip(X, y):
            pred = _lr_predict_proba(xi, coef, intercept)
            err  = pred - yi
            for j in range(n_feat):
                grad_coef[j] += err * xi[j]
            grad_int += err
        # L2 regularization + gradient step
        coef      = [c * (1 - lr * 0.01 / n_samples) - lr * grad_coef[j] / n_samples
                     for j, c in enumerate(coef)]
        intercept -= lr * grad_int / n_samples

    return coef, intercept


def _cross_val_accuracy(
    X: list[list[float]], y: list[int], coef: list[float], intercept: float
) -> float:
    """Simple last-20% holdout accuracy."""
    split = int(len(X) * 0.8)
    X_val, y_val = X[split:], y[split:]
    if not X_val:
        return 0.5
    correct = sum(
        1 for xi, yi in zip(X_val, y_val)
        if (1 if _lr_predict_proba(xi, coef, intercept) >= 0.5 else 0) == yi
    )
    return correct / len(X_val)


# ── Fetch intraday bars + RV from DB ──────────────────────────────────────────

async def _get_instrument_rv(db: AsyncSession, instrument_id: int) -> tuple[Optional[float], str]:
    r = await db.execute(text(
        "SELECT rv_30d, rv_regime FROM intel_snapshot WHERE instrument_id = :id"
    ), {"id": instrument_id})
    row = r.fetchone()
    if row and row[0]:
        return float(row[0]), "crypto" if instrument_id >= 16 else "fx"
    return None, "crypto" if instrument_id >= 16 else "fx"


# ── Train all models ──────────────────────────────────────────────────────────

async def train_all_models(db: AsyncSession) -> dict:
    """Build features from price_intraday, train per (instrument, horizon), store in DB."""
    results = {}
    now = datetime.now(timezone.utc)

    for inst_id in ML_INSTRUMENT_IDS:
        # Load all intraday bars (up to 30d)
        r = await db.execute(text("""
            SELECT ts, open, high, low, close, COALESCE(volume, 0)
            FROM price_intraday
            WHERE instrument_id = :id
            ORDER BY ts ASC
        """), {"id": inst_id})
        raw_bars = [(row[0], float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5]))
                    for row in r.fetchall()]

        if len(raw_bars) < 100:
            logger.warning("inst %d: only %d bars, skipping ML training", inst_id, len(raw_bars))
            results[inst_id] = {"error": "insufficient_data", "bars": len(raw_bars)}
            continue

        rv, asset_class = await _get_instrument_rv(db, inst_id)

        for horizon in HORIZONS:
            n_fwd = BARS_PER_HORIZON[horizon]

            # Build (X, y) pairs — slide a window of 60 bars, predict n_fwd bars ahead
            X_all: list[list[float]] = []
            y_all: list[int] = []
            window = 60

            for i in range(window, len(raw_bars) - n_fwd):
                window_bars = raw_bars[i - window:i]
                fv = _build_feature_vector(window_bars, rv, asset_class)
                if fv is None:
                    continue
                future_close = raw_bars[i + n_fwd - 1][4]
                current_close = raw_bars[i][4]
                label = 1 if future_close > current_close else 0
                X_all.append(fv)
                y_all.append(label)

            if len(X_all) < 50:
                logger.warning("inst %d h%d: only %d samples", inst_id, horizon, len(X_all))
                continue

            means, scales = _fit_scaler(X_all)
            X_scaled = [_apply_scaler(x, means, scales) for x in X_all]
            coef, intercept = _train_lr(X_scaled, y_all)
            acc = _cross_val_accuracy(X_scaled, y_all, coef, intercept)

            logger.info("inst %d h%dm: n=%d acc=%.3f", inst_id, horizon, len(X_all), acc)

            meta_row = {
                "instrument_id": inst_id,
                "horizon_minutes": horizon,
                "trained_at": now,
                "n_samples": len(X_all),
                "cv_accuracy": Decimal(str(round(acc, 4))),
                "feature_names_json": json.dumps(FEATURE_NAMES),
                "coef_json": json.dumps(coef),
                "intercept": Decimal(str(round(intercept, 8))),
                "scaler_mean_json": json.dumps(means),
                "scaler_scale_json": json.dumps(scales),
            }
            ins = pg_insert(MLModelMeta).values([meta_row])
            stmt = ins.on_conflict_do_update(
                index_elements=["instrument_id", "horizon_minutes"],
                set_={c: ins.excluded[c] for c in meta_row if c not in ("instrument_id", "horizon_minutes")},
            )
            await db.execute(stmt)
            results.setdefault(inst_id, {})[horizon] = {"acc": round(acc, 4), "n": len(X_all)}

    await db.commit()
    return results


# ── Live prediction (uses stored model weights) ───────────────────────────────

def _signal_from_prob(prob_up: float) -> tuple[str, str]:
    dist = abs(prob_up - 0.5)
    if dist < 0.05:
        return "neutral", "low"
    confidence = "high" if dist > 0.12 else "medium"
    signal = "bullish" if prob_up > 0.5 else "bearish"
    return signal, confidence


async def predict_instrument(
    db: AsyncSession, instrument_id: int
) -> Optional[dict[int, dict]]:
    """Return live {horizon: {prob_up, signal, confidence}} using stored model weights."""
    bars = await get_recent_bars(db, instrument_id, n_bars=80)
    if len(bars) < 60:
        return None

    rv, asset_class = await _get_instrument_rv(db, instrument_id)
    fv = _build_feature_vector(bars, rv, asset_class)
    if fv is None:
        return None

    # Load stored model weights for all horizons
    r = await db.execute(
        select(MLModelMeta).where(MLModelMeta.instrument_id == instrument_id)
    )
    models = {m.horizon_minutes: m for m in r.scalars().all()}

    if not models:
        return None

    predictions: dict[int, dict] = {}
    now = datetime.now(timezone.utc)

    for horizon, meta in models.items():
        if not meta.coef_json or not meta.scaler_mean_json:
            continue
        coef   = json.loads(meta.coef_json)
        means  = json.loads(meta.scaler_mean_json)
        scales = json.loads(meta.scaler_scale_json)
        intercept = float(meta.intercept)

        x_scaled = _apply_scaler(fv, means, scales)
        prob_up  = _lr_predict_proba(x_scaled, coef, intercept)
        signal, confidence = _signal_from_prob(prob_up)

        predictions[horizon] = {
            "prob_up": round(prob_up, 4),
            "signal": signal,
            "confidence": confidence,
        }

        pred_row = {
            "instrument_id": instrument_id,
            "horizon_minutes": horizon,
            "predicted_at": now,
            "prob_up": Decimal(str(round(prob_up, 4))),
            "signal": signal,
            "confidence": confidence,
        }
        ins = pg_insert(MLPrediction).values([pred_row])
        stmt = ins.on_conflict_do_update(
            index_elements=["instrument_id", "horizon_minutes"],
            set_={c: ins.excluded[c] for c in pred_row if c not in ("instrument_id", "horizon_minutes")},
        )
        await db.execute(stmt)

    await db.commit()
    return predictions


async def get_all_predictions(
    db: AsyncSession, instruments: list[Instrument]
) -> dict[int, dict]:
    """Return signals for all ML-eligible instruments (USDT excluded)."""
    result: dict[int, dict] = {}
    for inst in instruments:
        if inst.id not in ML_INSTRUMENT_IDS:
            # USDT or other pegged — return stable label
            result[inst.id] = {
                "symbol": inst.symbol,
                "is_peg": True,
                "predictions": {},
            }
            continue
        preds = await predict_instrument(db, inst.id)
        result[inst.id] = {
            "symbol": inst.symbol,
            "is_peg": False,
            "predictions": preds or {},
        }
    return result
