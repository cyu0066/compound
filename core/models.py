"""
Plain dataclasses for the three things Compound tracks. No Streamlit
dependency here on purpose, so this stays unit-testable on its own.
"""
from dataclasses import dataclass, asdict, field
from typing import Optional


@dataclass
class Holding:
    name: str
    ticker: str
    shares: float
    currency: str  # "AUD", "USD", or "NZD"
    platform: str = ""
    exchange: str = ""
    manual_price: Optional[float] = None
    live_price: Optional[float] = None
    price_source: str = "none"  # "live" | "manual" | "unavailable"

    @property
    def price(self) -> Optional[float]:
        """Best available price: live if we have it, else the manual fallback."""
        return self.live_price if self.live_price is not None else self.manual_price

    @property
    def value_native(self) -> Optional[float]:
        if self.price is None:
            return None
        return self.shares * self.price

    def to_dict(self) -> dict:
        """Only the user-entered fields — not the transient live_price/source."""
        return {
            "name": self.name,
            "ticker": self.ticker,
            "shares": self.shares,
            "currency": self.currency,
            "platform": self.platform,
            "exchange": self.exchange,
            "manual_price": self.manual_price,
        }


@dataclass
class Goal:
    name: str
    target_amount: float  # in AUD
    years: float  # years from now

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WatchlistItem:
    ticker: str
    note: str = ""
    live_price: Optional[float] = None
    prev_close: Optional[float] = None
    price_source: str = "none"

    @property
    def day_change_pct(self) -> Optional[float]:
        if self.live_price is None or not self.prev_close:
            return None
        return (self.live_price - self.prev_close) / self.prev_close * 100

    def to_dict(self) -> dict:
        return {"ticker": self.ticker, "note": self.note}
