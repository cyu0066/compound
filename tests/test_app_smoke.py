"""
Smoke tests: run the whole multi-page Streamlit app headlessly and check every
page renders without raising, and that settings survive moving between pages.
Live prices are switched off so the tests need no network.
Run with: pytest
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
APP_PATH = str(Path(__file__).parent.parent / "app.py")

PAGES = [
    "views/overview.py",
    "views/goals.py",
    "views/rebalance.py",
    "views/watchlist.py",
    "views/history.py",
    "views/settings.py",
]


def _fresh_app():
    at = AppTest.from_file(APP_PATH, default_timeout=60)
    at.session_state["use_live_prices"] = False  # stay offline
    at.run()
    return at


def _go(at, page):
    return at.switch_page(page).run()


def _target_inputs(at):
    return [n for n in at.number_input if n.key and n.key.startswith("target_")]


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_without_errors(page):
    at = _go(_fresh_app(), page)
    assert not at.exception, [e.message for e in at.exception]


def test_goals_page_shows_chance_of_reaching_each_goal():
    at = _go(_fresh_app(), "views/goals.py")
    labels = [m.label for m in at.metric]
    assert labels.count("Chance of reaching it") == 2  # the two example goals


def test_rebalance_starts_at_current_allocation_and_accepts_new_cash():
    at = _go(_fresh_app(), "views/rebalance.py")
    targets = _target_inputs(at)
    assert targets, "expected one target input per held ticker"
    assert sum(n.value for n in targets) == pytest.approx(100, abs=0.1)

    cash = next(n for n in at.number_input if n.label == "New cash to invest (AUD)")
    cash.set_value(1000).run()
    assert not at.exception, [e.message for e in at.exception]


def test_bad_targets_show_a_warning_instead_of_crashing():
    at = _go(_fresh_app(), "views/rebalance.py")
    first = _target_inputs(at)[0]
    first.set_value(first.value + 25).run()
    assert not at.exception, [e.message for e in at.exception]
    assert any("add up to" in w.value for w in at.warning)


def test_target_weights_survive_changing_page():
    at = _go(_fresh_app(), "views/rebalance.py")
    first = _target_inputs(at)[0]
    key, new_value = first.key, round(first.value + 5, 1)
    first.set_value(new_value).run()

    _go(at, "views/settings.py")
    at = _go(at, "views/rebalance.py")
    assert at.number_input(key=key).value == pytest.approx(new_value)


def test_goal_assumptions_survive_changing_page():
    at = _go(_fresh_app(), "views/goals.py")
    at.slider(key="monthly_contribution").set_value(1200).run()

    _go(at, "views/overview.py")
    at = _go(at, "views/goals.py")
    assert at.slider(key="monthly_contribution").value == 1200


def test_exchange_rates_survive_changing_page():
    at = _go(_fresh_app(), "views/settings.py")
    at.number_input(key="aud_usd").set_value(0.65).run()

    _go(at, "views/goals.py")
    at = _go(at, "views/settings.py")
    assert at.number_input(key="aud_usd").value == pytest.approx(0.65)


def test_saved_snapshot_appears_and_survives_changing_page():
    at = _go(_fresh_app(), "views/history.py")
    next(b for b in at.button if b.label.startswith("Save today's snapshot")).click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert len(at.session_state["history"]) == 1

    _go(at, "views/overview.py")
    at = _go(at, "views/history.py")
    assert len(at.session_state["history"]) == 1


# --- live data paths, with the network layer stubbed out ------------------------

def _live_app(monkeypatch, currency="USD", fx=None):
    import core.prices as prices
    monkeypatch.setattr(prices, "_fetch_quote", lambda t: (100.0, 99.0))
    monkeypatch.setattr(prices, "_fetch_currency", lambda t: currency)
    monkeypatch.setattr(prices, "fetch_fx_rates", lambda: fx or {"aud_usd": None, "aud_nzd": None})
    at = AppTest.from_file(APP_PATH, default_timeout=60)
    at.session_state["use_live_prices"] = True
    at.run()
    return at


def test_warns_when_a_holding_currency_differs_from_the_exchange(monkeypatch):
    at = _live_app(monkeypatch, currency="USD")
    assert not at.exception, [e.message for e in at.exception]
    warnings = [w.value for w in at.warning]
    assert any("IVV.AX" in w and "prices it in USD" in w for w in warnings)
    assert not any("AAPL" in w for w in warnings)  # AAPL really is USD


def test_no_currency_warning_when_everything_matches_offline():
    at = _fresh_app()
    assert not any("prices it in" in w.value for w in at.warning)


def test_live_exchange_rates_replace_the_manual_ones(monkeypatch):
    at = _live_app(monkeypatch, fx={"aud_usd": 0.5, "aud_nzd": 2.0})
    ctx = at.session_state["_ctx"]
    assert (ctx.aud_usd, ctx.aud_nzd, ctx.fx_source) == (0.5, 2.0, "live")


def test_falls_back_to_manual_rates_when_live_ones_fail(monkeypatch):
    at = _live_app(monkeypatch, fx={"aud_usd": 0.5, "aud_nzd": None})
    ctx = at.session_state["_ctx"]
    assert ctx.fx_source == "manual" and ctx.aud_usd == at.session_state["aud_usd"]


def test_manual_rates_used_when_live_rates_switched_off(monkeypatch):
    import core.prices as prices
    monkeypatch.setattr(prices, "fetch_fx_rates", lambda: {"aud_usd": 0.5, "aud_nzd": 2.0})
    at = _fresh_app()  # offline: live prices off, so live rates are not used
    assert at.session_state["_ctx"].fx_source == "manual"


# --- editing a holding ------------------------------------------------------------

def _edit_widget(at, prefix):
    matches = [w for w in list(at.number_input) + list(at.selectbox) if w.key and w.key.startswith(prefix)]
    assert len(matches) == 1, [w.key for w in matches]
    return matches[0]


def test_can_change_a_holdings_currency_and_shares():
    at = _fresh_app()
    before = at.session_state["holdings"]
    target = next(h for h in before if h.ticker == "USF.NZ")
    assert target.currency == "NZD"

    next(sb for sb in at.selectbox if sb.label == "Holding to edit").set_value(before.index(target)).run()
    _edit_widget(at, "edit_currency_").set_value("USD")
    _edit_widget(at, "edit_shares_").set_value(12.5)
    next(b for b in at.button if b.label == "Save changes").click().run()

    assert not at.exception, [e.message for e in at.exception]
    after = next(h for h in at.session_state["holdings"] if h.ticker == "USF.NZ")
    assert (after.currency, after.shares) == ("USD", 12.5)
    assert len(at.session_state["holdings"]) == len(before)


def test_edit_form_rejects_zero_shares():
    at = _fresh_app()
    _edit_widget(at, "edit_shares_").set_value(0)
    next(b for b in at.button if b.label == "Save changes").click().run()
    assert any("positive number of shares" in e.value for e in at.error)


def test_adding_same_ticker_at_another_broker_gives_one_row_with_both_brokers():
    at = _fresh_app()
    rows_before = len(at.session_state["_ctx"].df)
    first = next(h for h in at.session_state["holdings"] if h.ticker == "AAPL")
    original_shares, original_broker = first.shares, first.platform

    add_form = {t.label: t for t in at.text_input if not (t.key or "").startswith("edit_")}
    add_form["Ticker"].set_value("AAPL")
    add_form["Broker (optional)"].set_value("Broker B")
    next(sb for sb in at.selectbox if sb.label == "Currency" and not (sb.key or "").startswith("edit_")).set_value("USD")
    next(n for n in at.number_input if n.label == "Shares" and not (n.key or "").startswith("edit_")).set_value(2.5)
    next(b for b in at.button if b.label == "Add holding").click().run()

    assert not at.exception, [e.message for e in at.exception]
    df = at.session_state["_ctx"].df
    assert len(df) == rows_before  # no new row
    aapl = df[df["Ticker"] == "AAPL"].iloc[0]
    assert aapl["Shares"] == original_shares + 2.5
    assert "Broker B" in aapl["Platform"] and original_broker in aapl["Platform"]
