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
