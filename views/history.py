"""History: log snapshots of your portfolio value and see the real trajectory."""
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.state import HISTORY_PATH
from ui.theme import page_header, style_figure, money, ACCENT

ctx = st.session_state["_ctx"]

page_header(
    "History",
    "Log a snapshot each time you check in to build a record of how your portfolio really moved.",
)

history_df = (
    pd.read_csv(HISTORY_PATH, parse_dates=["date"]) if HISTORY_PATH.exists()
    else pd.DataFrame(columns=["date", "total_value_aud", "note"])
)

st.header("Save a snapshot")
with st.form("snapshot_form", clear_on_submit=True):
    note = st.text_input("Note (optional)")
    if st.form_submit_button(f"Save today's snapshot ({money(ctx.total_value)})"):
        new_row = pd.DataFrame([{"date": pd.Timestamp(date.today()), "total_value_aud": ctx.total_value, "note": note}])
        history_df = pd.concat([history_df, new_row], ignore_index=True)
        history_df.to_csv(HISTORY_PATH, index=False)
        st.success("Saved.")

st.header("Over time")
if len(history_df) > 0:
    fig = go.Figure(go.Scatter(
        x=history_df["date"], y=history_df["total_value_aud"], mode="lines+markers",
        line=dict(color=ACCENT, width=3), name="Portfolio value (AUD)",
    ))
    fig.update_layout(xaxis_title="Date", yaxis_title="Portfolio value (AUD)")
    st.plotly_chart(style_figure(fig, height=380), width="stretch")
else:
    st.info("No snapshots yet. Save one above.")
