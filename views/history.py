"""History: log snapshots of your portfolio value and see the real trajectory."""
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.theme import page_header, style_figure, money, ACCENT

ctx = st.session_state["_ctx"]

page_header(
    "History",
    "Log a snapshot each time you check in to build a record of how your portfolio really moved.",
)

st.caption(
    "Snapshots live in this browser session and are included in the file you download from Settings, "
    "so download after saving one or it will be lost when you close the tab."
)

st.header("Save a snapshot")
with st.form("snapshot_form", clear_on_submit=True):
    note = st.text_input("Note (optional)")
    if st.form_submit_button(f"Save today's snapshot ({money(ctx.total_value)})"):
        st.session_state.history.append(
            {"date": date.today().isoformat(), "total_value_aud": ctx.total_value, "note": note}
        )
        st.success("Saved.")

history_df = pd.DataFrame(st.session_state.history, columns=["date", "total_value_aud", "note"])
history_df["date"] = pd.to_datetime(history_df["date"])
history_df = history_df.sort_values("date")

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
