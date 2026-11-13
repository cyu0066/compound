"""Watchlist: tickers you're tracking but don't hold."""
import pandas as pd
import streamlit as st

from core.models import WatchlistItem
from core.prices import attach_watchlist_prices
from ui.theme import page_header

ctx = st.session_state["_ctx"]
watchlist = st.session_state.watchlist

page_header("Watchlist", "Tickers you're keeping an eye on but don't currently hold.")

if ctx.use_live_prices and watchlist:
    with st.spinner("Fetching watchlist prices..."):
        st.session_state.watchlist = watchlist = attach_watchlist_prices(watchlist)

st.header("Tracking")
if not watchlist:
    st.info("Nothing on your watchlist yet. Add a ticker below.")
else:
    table = pd.DataFrame([
        {"Ticker": w.ticker, "Price": w.live_price, "Day change (%)": w.day_change_pct, "Note": w.note}
        for w in watchlist
    ])
    st.dataframe(
        table, hide_index=True, width="stretch",
        column_config={
            "Price": st.column_config.NumberColumn(format="%.2f"),
            "Day change (%)": st.column_config.NumberColumn(format="%+.2f"),
        },
    )
    if not ctx.use_live_prices:
        st.caption("Live prices are switched off in Settings, so prices won't show here.")

st.header("Manage watchlist")
add_col, remove_col = st.columns(2)

with add_col:
    with st.expander("Add to watchlist", expanded=not watchlist):
        with st.form("add_watch_form", clear_on_submit=True):
            w_ticker = st.text_input("Ticker")
            w_note = st.text_input("Note (optional)")
            if st.form_submit_button("Add"):
                if not w_ticker:
                    st.error("Enter a ticker first.")
                else:
                    watchlist.append(WatchlistItem(ticker=w_ticker.upper().strip(), note=w_note))
                    st.rerun()

with remove_col:
    with st.expander("Remove from watchlist"):
        if not watchlist:
            st.caption("Nothing to remove.")
        else:
            index = st.selectbox("Ticker", range(len(watchlist)), format_func=lambda i: watchlist[i].ticker)
            if st.button("Remove"):
                watchlist.pop(index)
                st.rerun()
