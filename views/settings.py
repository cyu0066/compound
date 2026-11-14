"""Settings: price refresh, exchange rates, and saving/loading your data."""
import streamlit as st

from core.prices import clear_price_cache
from core.storage import bundle_to_json, bundle_from_json_str, targets_from_json_str, history_from_json_str
from ui.state import TARGET_KEY_PREFIX, saved_targets
from ui.theme import page_header

ctx = st.session_state["_ctx"]

page_header("Settings", "Prices, exchange rates, and your saved data.")

# --- Prices -----------------------------------------------------------------
st.header("Prices")
st.checkbox("Use live prices", key="use_live_prices",
            help="Fetch current prices from Yahoo Finance. Switch off to use your fallback prices only.")

if ctx.autorefresh_available:
    c1, c2 = st.columns(2)
    c1.checkbox("Keep prices updating automatically", key="auto_refresh")
    c2.slider("Refresh every (seconds)", 30, 300, step=30, key="refresh_seconds")
else:
    st.caption(
        "Install `streamlit-autorefresh` to enable hands-off refreshing. Prices still update "
        "whenever you use the app (cached for 30 seconds at a time)."
    )

if st.button("Refresh prices now"):
    clear_price_cache()
    st.rerun()

# --- Exchange rates ---------------------------------------------------------
st.header("Exchange rates")
st.checkbox(
    "Use live exchange rates", key="use_live_fx",
    help="Fetch AUD/USD and AUD/NZD from Yahoo Finance. Needs live prices switched on.",
)
if ctx.fx_source == "live":
    st.caption(f"Using live rates: 1 AUD = {ctx.aud_usd:.4f} USD = {ctx.aud_nzd:.4f} NZD.")
elif st.session_state.use_live_fx and st.session_state.use_live_prices:
    st.caption("Live rates couldn't be fetched just now, so the rates below are being used.")
st.caption(
    "How much of each currency one Australian dollar buys. These are used when live rates are "
    "switched off or unavailable."
)
r1, r2 = st.columns(2)
r1.number_input("AUD → USD", min_value=0.01, step=0.001, format="%.3f", key="aud_usd")
r2.number_input("AUD → NZD", min_value=0.01, step=0.001, format="%.3f", key="aud_nzd")

# --- Your data --------------------------------------------------------------
st.header("Your data")
st.caption(
    "Nothing here is saved on a server. Download your data before you close this tab, and upload "
    "it next time to pick up where you left off. The file holds your holdings, goals, watchlist, "
    "target allocation and history snapshots."
)

if flash := st.session_state.pop("_flash", None):
    st.success(flash)

export_json = bundle_to_json(
    st.session_state.holdings, st.session_state.goals, st.session_state.watchlist, saved_targets(),
    st.session_state.history,
)
st.download_button("Download my data", export_json, file_name="compound_data.json", mime="application/json")

uploaded = st.file_uploader("Upload my data", type="json")
if uploaded is not None:
    # The uploader keeps its file across reruns, so apply each file only once --
    # otherwise any edit made afterwards would be overwritten.
    upload_id = getattr(uploaded, "file_id", None) or (uploaded.name, uploaded.size)
    if st.session_state.get("last_upload_id") != upload_id:
        try:
            raw = uploaded.getvalue().decode("utf-8")
            holdings, goals, watchlist = bundle_from_json_str(raw)
            st.session_state.holdings, st.session_state.goals, st.session_state.watchlist = holdings, goals, watchlist
            st.session_state.history = history_from_json_str(raw)
            for ticker, weight in targets_from_json_str(raw).items():
                st.session_state[f"{TARGET_KEY_PREFIX}{ticker}"] = weight
            st.session_state.last_upload_id = upload_id
            st.session_state["_flash"] = "Data loaded."
            st.rerun()
        except Exception as e:  # a malformed file shouldn't crash the page
            st.error(f"Couldn't read that file: {e}")
