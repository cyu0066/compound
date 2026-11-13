"""
Compound — a self-updating personal portfolio, goals and rebalancing tracker.

This file is the entry point. It sets up the theme, loads shared data and prices,
then hands over to whichever page is selected (see views/).

Run locally with:
    streamlit run app.py
"""
from types import SimpleNamespace

import streamlit as st

from core.calculator import portfolio_summary
from core.prices import attach_live_prices
from ui.state import init_state, keep_widget_state
from ui.theme import apply_theme, DISCLAIMER

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

st.set_page_config(page_title="Compound", layout="wide", initial_sidebar_state="collapsed")
apply_theme()

# Each visitor's data lives in their own browser session; nothing is shared or stored on a server.
init_state()
keep_widget_state()

if AUTOREFRESH_AVAILABLE and st.session_state.auto_refresh:
    st_autorefresh(interval=int(st.session_state.refresh_seconds) * 1000, key="auto_refresh_timer")

# Value the portfolio once per run; every page reads the result from session state.
if st.session_state.use_live_prices:
    with st.spinner("Fetching live prices..."):
        st.session_state.holdings = attach_live_prices(st.session_state.holdings)

df = portfolio_summary(st.session_state.holdings, st.session_state.aud_usd, st.session_state.aud_nzd)
st.session_state["_ctx"] = SimpleNamespace(
    df=df,
    total_value=float(df["Value (AUD)"].sum(skipna=True)) if not df.empty else 0.0,
    missing=df[df["Value (AUD)"].isna()] if not df.empty else df,
    use_live_prices=st.session_state.use_live_prices,
    aud_usd=st.session_state.aud_usd,
    aud_nzd=st.session_state.aud_nzd,
    autorefresh_available=AUTOREFRESH_AVAILABLE,
)

navigation = st.navigation(
    [
        st.Page("views/overview.py", title="Overview", default=True),
        st.Page("views/goals.py", title="Goals"),
        st.Page("views/rebalance.py", title="Rebalance"),
        st.Page("views/watchlist.py", title="Watchlist"),
        st.Page("views/history.py", title="History"),
        st.Page("views/settings.py", title="Settings"),
    ],
    position="top",
)
navigation.run()

st.divider()
st.caption(DISCLAIMER)
