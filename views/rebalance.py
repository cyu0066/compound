"""Rebalance: set target weights and see what to buy or sell to reach them."""
import plotly.graph_objects as go
import streamlit as st

from core.rebalance import (
    current_weights_pct,
    equal_weights_pct,
    round_weights_to_100,
    rebalance_plan,
    WEIGHT_SUM_TOLERANCE,
)
from ui.state import TARGET_KEY_PREFIX
from ui.theme import page_header, style_figure, money

ctx = st.session_state["_ctx"]
df = ctx.df


def set_targets(weights: dict) -> None:
    """Button callback: write target weights into the number inputs' session state."""
    for ticker, weight in weights.items():
        st.session_state[f"{TARGET_KEY_PREFIX}{ticker}"] = float(weight)


page_header(
    "Rebalance",
    "Choose the allocation you want, and Compound shows what to buy or sell to get there. "
    "Holdings of the same ticker across different brokers are combined.",
)

priced = df.dropna(subset=["Value (AUD)"]) if not df.empty else df
if priced.empty:
    st.info("Add a holding with a valid price on the Overview page to plan a rebalance.")
    st.stop()

by_ticker = priced.groupby("Ticker").agg(
    value=("Value (AUD)", "sum"), shares=("Shares", "sum"), name=("Name", "first")
)
tickers = by_ticker.index.tolist()
current_values = by_ticker["value"].to_dict()
prices_aud = {t: current_values[t] / by_ticker.loc[t, "shares"] for t in tickers if by_ticker.loc[t, "shares"] > 0}
current_rounded = round_weights_to_100(current_weights_pct(current_values))

for t in tickers:  # first visit: start from the current allocation, so no trades yet
    st.session_state.setdefault(f"{TARGET_KEY_PREFIX}{t}", float(current_rounded[t]))

# --- Targets ----------------------------------------------------------------
st.header("Target allocation")
b1, b2, _ = st.columns([1.4, 1, 2])
b1.button("Match current allocation", on_click=set_targets, args=(current_rounded,))
b2.button("Equal weights", on_click=set_targets, args=(equal_weights_pct(tickers),))

target_cols = st.columns(min(len(tickers), 3))
for i, t in enumerate(tickers):
    target_cols[i % len(target_cols)].number_input(
        f"{t} — {by_ticker.loc[t, 'name']} (%)",
        min_value=0.0, max_value=100.0, step=0.5, format="%.1f",
        key=f"{TARGET_KEY_PREFIX}{t}",
    )
targets = {t: float(st.session_state[f"{TARGET_KEY_PREFIX}{t}"]) for t in tickers}
target_total = sum(targets.values())

# --- Options ----------------------------------------------------------------
st.header("How to get there")
o1, o2, o3 = st.columns(3)
new_cash = o1.number_input("New cash to invest (AUD)", min_value=0.0, step=100.0, value=0.0)
mode = o2.radio("Method", ["Buy only (no selling)", "Full rebalance (buy and sell)"])
tolerance = o3.slider(
    "Ignore drift within (percentage points)", 0.0, 10.0, 1.0, step=0.5,
    help="Holdings already this close to their target are left alone.",
)
allow_sells = mode.startswith("Full")

if abs(target_total - 100) > WEIGHT_SUM_TOLERANCE:
    st.warning(
        f"Your targets add up to {target_total:.1f}%. They need to total 100% "
        f"({100 - target_total:+.1f} to go)."
    )
    st.stop()

plan = rebalance_plan(
    current_values, targets, new_cash=new_cash, allow_sells=allow_sells,
    tolerance_pct=tolerance, prices=prices_aud,
)

# --- Result -----------------------------------------------------------------
st.header("Suggested trades")
buys = plan.loc[plan["Trade (AUD)"] > 0, "Trade (AUD)"].sum()
sells = -plan.loc[plan["Trade (AUD)"] < 0, "Trade (AUD)"].sum()

if buys == 0 and sells == 0:
    if allow_sells or new_cash > 0:
        st.success("Nothing to do: every holding is within your tolerance of its target.")
    else:
        st.info("Buy-only mode needs some new cash to invest. Add an amount above, or switch to a full rebalance.")
else:
    m1, m2 = st.columns(2)
    m1.metric("Total to buy", money(buys))
    m2.metric("Total to sell", money(sells))

st.dataframe(
    plan, hide_index=True, width="stretch",
    column_config={
        "Current value (AUD)": st.column_config.NumberColumn(format="$%.2f"),
        "Current %": st.column_config.NumberColumn(format="%.1f"),
        "Target %": st.column_config.NumberColumn(format="%.1f"),
        "Drift (pp)": st.column_config.NumberColumn(format="%+.1f"),
        "Trade (AUD)": st.column_config.NumberColumn(format="$%.2f"),
        "Value after (AUD)": st.column_config.NumberColumn(format="$%.2f"),
        "Approx. shares": st.column_config.NumberColumn(format="%+.4f"),
    },
)

chart = go.Figure()
chart.add_trace(go.Bar(x=plan["Ticker"], y=plan["Current %"], name="Current %"))
chart.add_trace(go.Bar(x=plan["Ticker"], y=plan["Target %"], name="Target %"))
chart.update_layout(barmode="group", yaxis_title="Share of portfolio (%)")
st.plotly_chart(style_figure(chart, height=360), width="stretch")

if allow_sells:
    st.caption(
        "Selling can trigger capital gains tax and brokerage fees, which this plan ignores. "
        "Buy-only mode avoids selling by steering new money towards underweight holdings."
    )
