from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum


class MarketState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    WEEKEND_GAP = "weekend_gap"


def get_fx_market_state(now: datetime | None = None) -> MarketState:
    """
    FX is approximately 24/5: opens Sunday 21:00 UTC, closes Friday 21:00 UTC.
    Weekends (Sat, or Sun before 21:00) → weekend_gap.
    Friday after 21:00 UTC → closed (post-NY close).
    Everything else Mon–Fri → open.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    weekday = now.weekday()  # 0=Mon … 6=Sun
    hour = now.hour

    if weekday == 5:  # Saturday
        return MarketState.WEEKEND_GAP
    if weekday == 6:  # Sunday
        return MarketState.OPEN if hour >= 21 else MarketState.WEEKEND_GAP
    if weekday == 4 and hour >= 21:  # Friday after 21:00 UTC
        return MarketState.CLOSED

    return MarketState.OPEN


def get_crypto_market_state() -> MarketState:
    return MarketState.OPEN
