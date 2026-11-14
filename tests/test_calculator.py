"""
Basic unit tests for core/calculator.py.
Run with: pytest
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.calculator import (
    to_aud,
    future_value,
    required_monthly_contribution,
    required_annual_return,
)
from core.models import Holding, Goal, WatchlistItem
from core.storage import bundle_to_json, bundle_from_json_str


def test_to_aud_same_currency():
    assert to_aud(100, "AUD", aud_usd=0.7, aud_nzd=1.2) == 100


def test_to_aud_usd():
    assert round(to_aud(70, "USD", aud_usd=0.7, aud_nzd=1.2), 2) == 100.0


def test_to_aud_nzd():
    assert round(to_aud(120, "NZD", aud_usd=0.7, aud_nzd=1.2), 2) == 100.0


def test_future_value_no_contribution():
    fv = future_value(1000, 0, 10, 1)
    expected = 1000 * (1 + 0.10 / 12) ** 12
    assert round(fv, 2) == round(expected, 2)


def test_future_value_with_contribution_matches_manual_sum():
    fv = future_value(1000, 100, 0, 1)
    assert round(fv, 2) == 1000 + 100 * 12


def test_required_monthly_contribution_roundtrip():
    present_value, goal, annual_return, years = 10_000, 1_000_000, 9.0, 10
    needed = required_monthly_contribution(present_value, goal, annual_return, years)
    fv = future_value(present_value, needed, annual_return, years)
    assert abs(fv - goal) < 1.0


def test_required_annual_return_roundtrip():
    present_value, goal, monthly_contribution, years = 10_000, 1_000_000, 1_500, 10
    needed = required_annual_return(present_value, goal, monthly_contribution, years)
    assert needed is not None
    fv = future_value(present_value, monthly_contribution, needed, years)
    assert abs(fv - goal) < 5.0


def test_required_annual_return_unreachable_returns_none():
    needed = required_annual_return(present_value=10, goal=10_000_000, monthly_contribution=1, years=1)
    assert needed is None


def test_holding_value_native_none_without_price():
    h = Holding(name="Test", ticker="TST", shares=10, currency="USD")
    assert h.price is None
    assert h.value_native is None


def test_holding_value_native_uses_manual_price_fallback():
    h = Holding(name="Test", ticker="TST", shares=10, currency="USD", manual_price=5.0)
    assert h.price == 5.0
    assert h.value_native == 50.0


def test_holding_prefers_live_price_over_manual():
    h = Holding(name="Test", ticker="TST", shares=10, currency="USD", manual_price=5.0)
    h.live_price = 6.0
    assert h.price == 6.0


def test_bundle_roundtrip():
    holdings = [Holding(name="Apple", ticker="AAPL", shares=1, currency="USD", manual_price=331.206)]
    goals = [Goal(name="Test goal", target_amount=1000, years=2)]
    watchlist = [WatchlistItem(ticker="TSLA")]

    packed = bundle_to_json(holdings, goals, watchlist)
    h2, g2, w2 = bundle_from_json_str(packed)

    assert h2[0].ticker == "AAPL"
    assert h2[0].manual_price == 331.206
    assert g2[0].target_amount == 1000
    assert w2[0].ticker == "TSLA"


# --- the same ticker at several brokers ----------------------------------------

def test_same_ticker_at_two_brokers_becomes_one_row():
    from core.calculator import portfolio_summary, combine_by_ticker
    from core.models import Holding
    holdings = [
        Holding(name="NVIDIA Corp", ticker="NVDA", shares=3.0, currency="USD", platform="Broker A", manual_price=100.0),
        Holding(name="NVIDIA", ticker="NVDA", shares=4.2014, currency="USD", platform="Broker B", manual_price=100.0),
        Holding(name="Visa", ticker="V", shares=1.0, currency="USD", platform="Broker B", manual_price=50.0),
    ]
    combined = combine_by_ticker(portfolio_summary(holdings, aud_usd=0.5, aud_nzd=1.1))
    nvda = combined[combined["Ticker"] == "NVDA"].iloc[0]
    assert len(combined) == 2
    assert nvda["Shares"] == 7.2014
    assert nvda["Platform"] == "Broker A, Broker B"
    assert nvda["Value (AUD)"] == 7.2014 * 100.0 / 0.5


def test_same_ticker_in_different_currencies_stays_separate():
    from core.calculator import portfolio_summary, combine_by_ticker
    from core.models import Holding
    holdings = [
        Holding(name="NVDA", ticker="NVDA", shares=1, currency="USD", manual_price=100.0),
        Holding(name="NVDA", ticker="NVDA", shares=1, currency="NZD", manual_price=100.0),
    ]
    assert len(combine_by_ticker(portfolio_summary(holdings, 0.5, 1.1))) == 2


def test_combining_keeps_a_row_with_no_price_as_missing():
    import math
    from core.calculator import portfolio_summary, combine_by_ticker
    from core.models import Holding
    holdings = [Holding(name="X", ticker="X", shares=1, currency="USD", platform="A")]
    combined = combine_by_ticker(portfolio_summary(holdings, 0.5, 1.1))
    assert math.isnan(combined["Value (AUD)"].iloc[0])


def test_combining_an_empty_table_is_fine():
    import pandas as pd
    from core.calculator import combine_by_ticker
    assert combine_by_ticker(pd.DataFrame()).empty
