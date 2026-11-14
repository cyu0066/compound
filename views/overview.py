"""Overview: portfolio value, holdings table, allocation, and adding/removing holdings."""
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.checks import currency_mismatches
from core.models import Holding
from ui.theme import page_header, style_figure, money

ctx = st.session_state["_ctx"]
df = ctx.df
holdings = st.session_state.holdings

page_header("Overview", f"Your portfolio as of {date.today():%d %B %Y}, valued in Australian dollars.")

live_count = int((df["Price source"] == "live").sum()) if not df.empty else 0
m1, m2, m3 = st.columns(3)
m1.metric("Total portfolio value", f"{money(ctx.total_value)} AUD")
m2.metric("Holdings", len(df))
m3.metric("Live prices", f"{live_count} of {len(df)}" if not df.empty else "0 of 0")

if ctx.fx_source == "live":
    st.caption(f"Exchange rates are live: 1 AUD = {ctx.aud_usd:.4f} USD = {ctx.aud_nzd:.4f} NZD.")
else:
    st.caption(
        f"Exchange rates are set by hand: 1 AUD = {ctx.aud_usd:.4f} USD = {ctx.aud_nzd:.4f} NZD. "
        "You can switch to live rates in Settings."
    )

warned = set()
for h, reported in currency_mismatches(holdings):
    if (h.ticker, h.currency) in warned:
        continue
    warned.add((h.ticker, h.currency))
    st.warning(
        f"**{h.name} ({h.ticker})** is entered in {h.currency}, but Yahoo Finance prices it in {reported}. "
        f"If the price is really in {reported}, the value shown is wrong. Fix it under Edit a holding below."
    )

if not ctx.missing.empty:
    st.warning(
        "No price available for: " + ", ".join(ctx.missing["Ticker"].tolist())
        + ". These are left out of the total until a live price works or you set a fallback price."
    )

# --- Holdings table ---------------------------------------------------------
st.header("Holdings")
if df.empty:
    st.info("No holdings yet. Add one below.")
else:
    table = df[["Name", "Ticker", "Platform", "Shares", "Currency", "Price (native)", "Value (AUD)", "Price source"]]
    st.dataframe(
        table, hide_index=True, width="stretch",
        column_config={
            "Platform": st.column_config.TextColumn("Broker"),
            "Shares": st.column_config.NumberColumn(format="%.4f"),
            "Price (native)": st.column_config.NumberColumn("Price", format="%.2f"),
            "Value (AUD)": st.column_config.NumberColumn(format="$%.2f"),
            "Price source": st.column_config.TextColumn("Price from"),
        },
    )

# --- Allocation chart -------------------------------------------------------
st.header("Allocation")
alloc = df.dropna(subset=["Value (AUD)"]).groupby("Name")["Value (AUD)"].sum() if not df.empty else pd.Series(dtype=float)
if len(alloc) > 0:
    fig = go.Figure(go.Pie(labels=alloc.index, values=alloc.values, hole=0.5, sort=True, textinfo="percent"))
    fig.update_layout(legend=dict(orientation="v", y=0.5, yanchor="middle", x=1.02))
    st.plotly_chart(style_figure(fig, height=380), width="stretch")
else:
    st.caption("Add a holding with a valid price to see your allocation.")

# --- Manage holdings --------------------------------------------------------
CURRENCIES = ["AUD", "USD", "NZD"]

st.header("Manage holdings")

with st.expander("Add a holding", expanded=not holdings):
    st.caption(
        "Own the same stock at more than one broker? Add it once per broker with that broker's shares. "
        "The holdings table combines them into a single row."
    )
    with st.form("add_holding_form", clear_on_submit=True):
        name = st.text_input("Name")
        ticker = st.text_input("Ticker", help="As recognised by Yahoo Finance, e.g. AAPL or IVV.AX")
        c1, c2 = st.columns(2)
        shares = c1.number_input("Shares", min_value=0.0, step=0.01, format="%.4f")
        currency = c2.selectbox("Currency", CURRENCIES)
        manual_price = st.number_input(
            "Fallback price (optional)", min_value=0.0, step=0.01,
            help="Used only if a live price can't be fetched for this ticker.",
        )
        platform = st.text_input("Broker (optional)")
        if st.form_submit_button("Add holding"):
            if not ticker or shares <= 0:
                st.error("Enter a ticker and a positive number of shares.")
            else:
                holdings.append(Holding(
                    name=name or ticker, ticker=ticker.upper().strip(), shares=shares,
                    currency=currency, platform=platform,
                    manual_price=manual_price if manual_price > 0 else None,
                ))
                st.rerun()


def _label(i: int) -> str:
    h = holdings[i]
    return f"{h.name} ({h.ticker}" + (f", {h.platform}" if h.platform else "") + ")"


with st.expander("Edit a holding"):
    if not holdings:
        st.caption("Nothing to edit.")
    else:
        edit_index = st.selectbox("Holding to edit", range(len(holdings)), format_func=_label)
        h = holdings[edit_index]
        # The widget keys include the holding's current values, so the form refills
        # whenever a different holding is chosen or this one is saved.
        sig = f"{edit_index}_{h.ticker}_{h.platform}_{h.shares}_{h.currency}_{h.manual_price}_{h.name}"
        with st.form(f"edit_holding_form_{sig}"):
            e_name = st.text_input("Name", value=h.name, key=f"edit_name_{sig}")
            e_ticker = st.text_input("Ticker", value=h.ticker, key=f"edit_ticker_{sig}")
            e1, e2 = st.columns(2)
            e_shares = e1.number_input("Shares", min_value=0.0, step=0.01, format="%.4f",
                                       value=float(h.shares), key=f"edit_shares_{sig}")
            e_currency = e2.selectbox("Currency", CURRENCIES, index=CURRENCIES.index(h.currency)
                                      if h.currency in CURRENCIES else 0, key=f"edit_currency_{sig}")
            e_price = st.number_input("Fallback price (optional)", min_value=0.0, step=0.01,
                                      value=float(h.manual_price or 0.0), key=f"edit_price_{sig}")
            e_platform = st.text_input("Broker (optional)", value=h.platform, key=f"edit_platform_{sig}")
            if st.form_submit_button("Save changes"):
                if not e_ticker.strip() or e_shares <= 0:
                    st.error("Enter a ticker and a positive number of shares.")
                else:
                    holdings[edit_index] = Holding(
                        name=e_name or e_ticker, ticker=e_ticker.upper().strip(), shares=e_shares,
                        currency=e_currency, platform=e_platform, exchange=h.exchange,
                        manual_price=e_price if e_price > 0 else None,
                    )
                    st.rerun()

with st.expander("Remove a holding"):
    if not holdings:
        st.caption("Nothing to remove.")
    else:
        index = st.selectbox("Holding", range(len(holdings)), format_func=_label)
        if st.button("Remove holding"):
            holdings.pop(index)
            st.rerun()
