from __future__ import annotations

import math
from typing import Optional


def rsi(prices: list[float], period: int = 14) -> Optional[float]:
    """Wilder's RSI. Returns 0–100, or None if insufficient data."""
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i - 1]
        gains.append(max(0.0, d))
        losses.append(max(0.0, -d))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    return round(100.0 - 100.0 / (1 + avg_g / avg_l), 2)


def bollinger_pct_b(prices: list[float], period: int = 20, k: float = 2.0) -> Optional[float]:
    """Bollinger Band %B: 0 = lower band, 1 = upper band. <0 below, >1 above."""
    if len(prices) < period:
        return None
    window = prices[-period:]
    mean = sum(window) / period
    variance = sum((x - mean) ** 2 for x in window) / period
    std = math.sqrt(variance)
    if std == 0:
        return None
    upper = mean + k * std
    lower = mean - k * std
    return round((prices[-1] - lower) / (upper - lower), 4)


def sma(prices: list[float], period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def sma_trend(prices: list[float], fast: int = 7, slow: int = 21) -> Optional[str]:
    """'bullish' when fast SMA > slow SMA, 'bearish' otherwise."""
    f = sma(prices, fast)
    s = sma(prices, slow)
    if f is None or s is None:
        return None
    return "bullish" if f > s else "bearish"


def ta_composite(
    rsi_val: Optional[float],
    bb_val: Optional[float],
    trend: Optional[str],
    regime: Optional[str],
) -> tuple[str, str]:
    """
    Returns (composite_label, reasoning_string).
    composite_label: 'lean_long' | 'lean_short' | 'neutral' | 'suppressed'
    Regime filter: extreme vol suppresses all signals.
    """
    if regime == "extreme":
        return "suppressed", "Extreme volatility — signals suppressed"

    bull, bear = 0, 0
    reasons: list[str] = []

    if rsi_val is not None:
        if rsi_val < 30:
            bull += 1
            reasons.append(f"RSI {rsi_val:.1f} oversold")
        elif rsi_val > 70:
            bear += 1
            reasons.append(f"RSI {rsi_val:.1f} overbought")
        else:
            reasons.append(f"RSI {rsi_val:.1f}")

    if bb_val is not None:
        if bb_val < 0:
            bull += 1
            reasons.append(f"BB%B {bb_val:.2f} below band")
        elif bb_val > 1:
            bear += 1
            reasons.append(f"BB%B {bb_val:.2f} above band")
        else:
            reasons.append(f"BB%B {bb_val:.2f}")

    if trend is not None:
        if trend == "bullish":
            bull += 1
            reasons.append("SMA7>SMA21 ↑")
        else:
            bear += 1
            reasons.append("SMA7<SMA21 ↓")

    reasoning = " · ".join(reasons) if reasons else "No data"

    total = bull + bear
    if total == 0:
        return "neutral", reasoning
    if bull >= 2 and bull > bear:
        return "lean_long", reasoning
    if bear >= 2 and bear > bull:
        return "lean_short", reasoning
    return "neutral", reasoning
