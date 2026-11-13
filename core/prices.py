"""
Live price fetching, with short-TTL caching so an auto-refreshing app
doesn't hammer the upstream API on every rerun.
"""
from typing import Optional

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

CACHE_TTL_SECONDS = 30
HISTORY_TTL_SECONDS = 3600  # daily history barely changes, so cache it for an hour


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_quote(ticker: str) -> tuple[Optional[float], Optional[float]]:
    """
    Returns (last_price, previous_close). Either can be None if unavailable.
    Cached per-ticker for CACHE_TTL_SECONDS so a page with auto-refresh on
    doesn't re-hit the API faster than that, even across many holdings.
    """
    if not YFINANCE_AVAILABLE:
        return None, None
    try:
        info = yf.Ticker(ticker).fast_info
        last = info.get("lastPrice") or info.get("last_price")
        prev = info.get("previousClose") or info.get("previous_close") \
            or info.get("regularMarketPreviousClose")
        return (float(last) if last else None, float(prev) if prev else None)
    except Exception:
        return None, None


def attach_live_prices(holdings: list) -> list:
    """Mutates each Holding in place with live_price/price_source, then returns the list."""
    for h in holdings:
        last, _ = _fetch_quote(h.ticker)
        if last is not None:
            h.live_price = last
            h.price_source = "live"
        else:
            h.live_price = None
            h.price_source = "manual" if h.manual_price is not None else "unavailable"
    return holdings


def attach_watchlist_prices(items: list) -> list:
    for it in items:
        last, prev = _fetch_quote(it.ticker)
        it.live_price = last
        it.prev_close = prev
        it.price_source = "live" if last is not None else "unavailable"
    return items


@st.cache_data(ttl=HISTORY_TTL_SECONDS, show_spinner=False)
def _fetch_history(ticker: str, period: str = "2y") -> Optional[pd.Series]:
    """Daily closing prices for one ticker, indexed by date. None if unavailable."""
    if not YFINANCE_AVAILABLE:
        return None
    try:
        hist = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        closes = hist["Close"].dropna()
        if closes.empty:
            return None
        # Normalise to plain dates so tickers from different exchanges line up.
        closes.index = pd.to_datetime(closes.index.date)
        return closes
    except Exception:
        return None


def fetch_price_history(tickers) -> pd.DataFrame:
    """One column of daily closes per ticker that has history; empty DataFrame if none."""
    series = {}
    for t in tickers:
        s = _fetch_history(t)
        if s is not None:
            series[t] = s
    return pd.DataFrame(series) if series else pd.DataFrame()


def clear_price_cache():
    _fetch_quote.clear()
    _fetch_history.clear()
