"""Goals: Monte Carlo chance of reaching each goal, what it would take, and a fan chart."""
import plotly.graph_objects as go
import streamlit as st

from core.calculator import (
    projection_series,
    required_monthly_contribution,
    required_annual_return,
)
from core.models import Goal
from core.montecarlo import (
    simulate_paths,
    probability_of_goal,
    outcome_percentiles,
    percentile_bands,
    portfolio_volatility,
)
from core.prices import fetch_price_history
from ui.state import N_SIMULATIONS
from ui.theme import page_header, style_figure, money, compact_money, years_label, ACCENT

ctx = st.session_state["_ctx"]
df = ctx.df
goals = st.session_state.goals

page_header(
    "Goals",
    "How likely you are to reach each goal, and what it would take. Results come from simulating "
    f"{N_SIMULATIONS:,} possible futures rather than assuming one smooth line.",
)

# --- Assumptions ------------------------------------------------------------
with st.expander("Assumptions", expanded=True):
    a1, a2 = st.columns(2)
    a1.slider("Monthly contribution (AUD)", 0, 5_000, step=50, key="monthly_contribution")
    a2.slider("Assumed annual return (%)", 0.0, 30.0, step=0.5, key="annual_return_pct")
    b1, b2 = st.columns(2)
    b1.checkbox(
        "Estimate volatility from my holdings' history", key="estimate_vol",
        help="Uses about two years of daily prices. Needs live prices and an internet connection; "
             "otherwise the figure on the right is used.",
    )
    b2.slider(
        "Volatility to assume otherwise (%)", 5.0, 80.0, step=1.0, key="manual_vol",
        help="How much returns swing from year to year. Broad stock indexes are often around 15%; "
             "a portfolio of a few single stocks is usually higher.",
    )

monthly_contribution = st.session_state.monthly_contribution
annual_return_pct = st.session_state.annual_return_pct
total_value = ctx.total_value

# Volatility: estimated from price history when possible, otherwise the manual figure.
annual_vol_pct = st.session_state.manual_vol
vol_source = "assumed"
if st.session_state.estimate_vol and ctx.use_live_prices and not df.empty:
    values_by_ticker = df.dropna(subset=["Value (AUD)"]).groupby("Ticker")["Value (AUD)"].sum()
    if not values_by_ticker.empty:
        history = fetch_price_history(list(values_by_ticker.index))
        estimate = portfolio_volatility(history, (values_by_ticker / values_by_ticker.sum()).to_dict())
        if estimate is not None:
            annual_vol_pct, vol_source = estimate, "estimated from your holdings' price history"

st.caption(
    f"Starting from your current portfolio of **{money(total_value)}**, adding **{money(monthly_contribution, cents=False)} a month** "
    f"at **{annual_return_pct:.1f}%** expected return and **{annual_vol_pct:.0f}% volatility** ({vol_source}). "
    "The random seed is fixed, so results stay steady when the page refreshes."
)

# --- Simulate once for the longest goal; each goal reads its own month ------
mc_paths = None
if goals:
    mc_paths = simulate_paths(
        total_value, monthly_contribution, annual_return_pct, annual_vol_pct,
        years=max(g.years for g in goals), n_sims=N_SIMULATIONS,
    )

st.header("Your goals")
if not goals:
    st.info("No goals yet. Add one below.")

for i, g in enumerate(goals):
    month = int(round(g.years * 12))
    chance = probability_of_goal(mc_paths, g.target_amount, month)
    spread = outcome_percentiles(mc_paths, month)
    needed_contribution = required_monthly_contribution(total_value, g.target_amount, annual_return_pct, g.years)
    needed_return = required_annual_return(total_value, g.target_amount, monthly_contribution, g.years)
    progress = min(total_value / g.target_amount, 1.0) if g.target_amount > 0 else 0.0
    fixed_final = projection_series(total_value, monthly_contribution, annual_return_pct, g.years)["value_aud"].iloc[-1]

    with st.container(border=True):
        top = st.columns([5, 1])
        top[0].subheader(g.name)
        top[0].caption(f"{money(g.target_amount, cents=False)} in {years_label(g.years)}")
        if top[1].button("Remove", key=f"del_goal_{i}"):
            goals.pop(i)
            st.rerun()

        st.progress(progress, text=f"{progress:.0%} of the way there today")

        k1, k2, k3 = st.columns(3)
        k1.metric("Chance of reaching it", f"{chance:.0%}")
        k2.metric("Typical outcome", compact_money(spread[50]))
        k3.metric("Needed per month", compact_money(needed_contribution) if needed_contribution > 0 else "None")

        if needed_return is None:
            return_line = "Not reachable at this contribution level within a realistic return range."
        elif needed_return <= -49.9:  # solver hit its lower bound: the goal is met regardless
            return_line = f"Reached at {money(monthly_contribution, cents=False)} a month even with a very poor return."
        else:
            return_line = (
                f"At {money(monthly_contribution, cents=False)} a month you would need about "
                f"**{needed_return:.1f}% a year** to reach it on time."
            )
        st.caption(
            f"A poor run (10th percentile) ends near {compact_money(spread[10])} and a good run "
            f"(90th percentile) near {compact_money(spread[90])}. {return_line} "
            f"A fixed-return projection gives {money(fixed_final, cents=False)} after {years_label(g.years)}."
        )

with st.expander("Add a goal"):
    with st.form("add_goal_form", clear_on_submit=True):
        goal_name = st.text_input("Goal name")
        c1, c2 = st.columns(2)
        goal_amount = c1.number_input("Target amount (AUD)", min_value=0.0, step=1000.0)
        goal_years = c2.number_input("Years from now", min_value=0.1, step=0.5, value=5.0)
        if st.form_submit_button("Add goal"):
            if not goal_name or goal_amount <= 0:
                st.error("Enter a name and a positive target amount.")
            else:
                goals.append(Goal(name=goal_name, target_amount=goal_amount, years=goal_years))
                st.rerun()

# --- Fan chart --------------------------------------------------------------
if goals:
    st.header("All goals together")
    max_years = max(g.years for g in goals)
    fixed = projection_series(total_value, monthly_contribution, annual_return_pct, max_years)
    fixed["years"] = fixed["month"] / 12
    bands = percentile_bands(mc_paths)
    bands["years"] = bands["month"] / 12

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=bands["years"], y=bands["p90"], mode="lines", line=dict(width=0),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=bands["years"], y=bands["p10"], mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor="rgba(47,107,90,0.16)", name="Middle 80% of outcomes"))
    fig.add_trace(go.Scatter(x=bands["years"], y=bands["p50"], mode="lines", line=dict(color=ACCENT, width=3),
                             name="Median simulated outcome"))
    fig.add_trace(go.Scatter(x=fixed["years"], y=fixed["value_aud"], mode="lines",
                             line=dict(dash="dash", color="#8a8f98"), name="Fixed-return projection"))
    for g in goals:
        fig.add_hline(y=g.target_amount, line_dash="dot", line_color="#C08A3E",
                      annotation_text=g.name, annotation_position="top left")
    fig.update_layout(xaxis_title="Years from now", yaxis_title="Portfolio value (AUD)")
    st.plotly_chart(style_figure(fig, height=460), width="stretch")
