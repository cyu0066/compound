"""
Shared constants and session-state setup used by every page.

Streamlit drops a widget's value when you navigate to a page that doesn't draw
that widget. Settings and target weights need to survive page changes, so
`keep_widget_state` re-saves them on every run.
"""
from pathlib import Path

import streamlit as st

from core.storage import load_holdings, load_goals, load_watchlist

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
HISTORY_PATH = DATA_DIR / "history.csv"

TARGET_KEY_PREFIX = "target_"  # rebalancing target weights, one key per ticker
N_SIMULATIONS = 5_000
DEFAULT_VOLATILITY_PCT = 15.0

# Widget keys that must persist across pages, with their starting values.
SETTING_DEFAULTS = {
    "use_live_prices": True,
    "auto_refresh": False,
    "refresh_seconds": 60,
    "aud_usd": 0.717,
    "aud_nzd": 1.225,
    "monthly_contribution": 500,
    "annual_return_pct": 9.0,
    "estimate_vol": True,
    "manual_vol": DEFAULT_VOLATILITY_PCT,
}


def init_state() -> None:
    """Load the starter data once per session and set default settings."""
    if "holdings" not in st.session_state:
        st.session_state.holdings = load_holdings(DATA_DIR / "portfolio.json")
    if "goals" not in st.session_state:
        st.session_state.goals = load_goals(DATA_DIR / "goals.json")
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = load_watchlist(DATA_DIR / "watchlist.json")
    for key, value in SETTING_DEFAULTS.items():
        st.session_state.setdefault(key, value)


def keep_widget_state() -> None:
    """Stop Streamlit discarding settings and targets when a page doesn't draw them."""
    for key in list(st.session_state.keys()):
        if key in SETTING_DEFAULTS or key.startswith(TARGET_KEY_PREFIX):
            st.session_state[key] = st.session_state[key]


def saved_targets() -> dict:
    """Target weights ({ticker: percent}) for tickers currently held."""
    held = {h.ticker for h in st.session_state.holdings}
    return {
        key[len(TARGET_KEY_PREFIX):]: value
        for key, value in st.session_state.items()
        if key.startswith(TARGET_KEY_PREFIX) and key[len(TARGET_KEY_PREFIX):] in held
    }
