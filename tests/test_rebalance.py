"""
Unit tests for core/rebalance.py.
Run with: pytest
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.rebalance import (
    current_weights_pct,
    equal_weights_pct,
    round_weights_to_100,
    rebalance_plan,
)

VALUES = {"AAA": 6000.0, "BBB": 3000.0, "CCC": 1000.0}  # 60 / 30 / 10
TARGETS = {"AAA": 40.0, "BBB": 40.0, "CCC": 20.0}


def _row(df, ticker):
    return df[df["Ticker"] == ticker].iloc[0]


def test_current_weights_sum_to_100():
    w = current_weights_pct(VALUES)
    assert sum(w.values()) == pytest.approx(100)
    assert w["AAA"] == pytest.approx(60)


def test_equal_weights_sum_to_exactly_100():
    for n in (1, 3, 6, 7):
        tickers = [f"T{i}" for i in range(n)]
        assert sum(equal_weights_pct(tickers).values()) == pytest.approx(100)


def test_round_weights_to_100():
    w = round_weights_to_100({"A": 33.333, "B": 33.333, "C": 33.334})
    assert sum(w.values()) == pytest.approx(100)


def test_full_rebalance_reaches_targets():
    df = rebalance_plan(VALUES, TARGETS, allow_sells=True)
    total = sum(VALUES.values())
    for t, pct in TARGETS.items():
        assert _row(df, t)["Value after (AUD)"] == pytest.approx(pct / 100 * total)
    assert df["Trade (AUD)"].sum() == pytest.approx(0)  # sells fund the buys


def test_full_rebalance_with_new_cash_adds_cash_to_portfolio():
    df = rebalance_plan(VALUES, TARGETS, new_cash=2000, allow_sells=True)
    assert df["Trade (AUD)"].sum() == pytest.approx(2000)
    assert df["Value after (AUD)"].sum() == pytest.approx(12000)


def test_buy_only_never_sells_and_spends_exactly_the_cash():
    df = rebalance_plan(VALUES, TARGETS, new_cash=2000, allow_sells=False)
    assert (df["Trade (AUD)"] >= 0).all()
    assert df["Trade (AUD)"].sum() == pytest.approx(2000)
    assert _row(df, "AAA")["Action"] == "Hold"  # overweight, so it gets nothing


def test_buy_only_with_no_cash_does_nothing():
    df = rebalance_plan(VALUES, TARGETS, new_cash=0, allow_sells=False)
    assert (df["Action"] == "Hold").all()


def test_buy_only_favours_the_most_underweight_holding():
    df = rebalance_plan(VALUES, TARGETS, new_cash=500, allow_sells=False)
    assert _row(df, "BBB")["Trade (AUD)"] > 0
    assert _row(df, "CCC")["Trade (AUD)"] > 0


def test_tolerance_leaves_near_target_holdings_alone():
    near = {"AAA": 5050.0, "BBB": 4950.0}  # 50.5 / 49.5
    df = rebalance_plan(near, {"AAA": 50.0, "BBB": 50.0}, allow_sells=True, tolerance_pct=2)
    assert (df["Action"] == "Hold").all()


def test_targets_must_sum_to_100():
    with pytest.raises(ValueError):
        rebalance_plan(VALUES, {"AAA": 50.0, "BBB": 30.0, "CCC": 10.0})


def test_negative_targets_or_cash_rejected():
    with pytest.raises(ValueError):
        rebalance_plan(VALUES, {"AAA": 120.0, "BBB": -20.0, "CCC": 0.0})
    with pytest.raises(ValueError):
        rebalance_plan(VALUES, TARGETS, new_cash=-1)


def test_new_ticker_in_targets_is_bought():
    df = rebalance_plan({"AAA": 1000.0}, {"AAA": 50.0, "NEW": 50.0}, new_cash=1000, allow_sells=False)
    assert _row(df, "NEW")["Trade (AUD)"] == pytest.approx(1000)


def test_approx_shares_uses_prices():
    df = rebalance_plan(VALUES, TARGETS, allow_sells=True, prices={"AAA": 100.0, "BBB": 50.0, "CCC": 25.0})
    assert _row(df, "AAA")["Approx. shares"] == pytest.approx(_row(df, "AAA")["Trade (AUD)"] / 100.0)
