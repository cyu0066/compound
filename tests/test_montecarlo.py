"""
Unit tests for core/montecarlo.py.
Run with: pytest
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.montecarlo import (
    simulate_paths,
    probability_of_goal,
    outcome_percentiles,
    percentile_bands,
    portfolio_volatility,
)


def test_paths_shape_and_start_value():
    paths = simulate_paths(1000, 100, 8, 15, years=2, n_sims=50)
    assert paths.shape == (50, 25)
    assert np.all(paths[:, 0] == 1000)


def test_same_seed_is_reproducible():
    a = simulate_paths(1000, 100, 8, 15, years=3, n_sims=200, seed=7)
    b = simulate_paths(1000, 100, 8, 15, years=3, n_sims=200, seed=7)
    assert np.array_equal(a, b)


def test_zero_volatility_matches_closed_form():
    # With no randomness each month multiplies by exp(mu/12), then adds a contribution.
    pv, contrib, mu, years = 10_000, 500, 0.09, 5
    paths = simulate_paths(pv, contrib, mu * 100, 0, years=years, n_sims=3)
    m = mu / 12
    n = years * 12
    expected = pv * np.exp(m * n) + contrib * (np.exp(m * n) - 1) / (np.exp(m) - 1)
    assert np.allclose(paths[:, -1], expected)


def test_average_outcome_matches_assumed_return():
    # With no contributions, E[final] = PV * exp(mu * T) regardless of volatility.
    pv, mu, years = 10_000, 0.08, 5
    paths = simulate_paths(pv, 0, mu * 100, 20, years=years, n_sims=40_000, seed=1)
    expected = pv * np.exp(mu * years)
    assert paths[:, -1].mean() == pytest.approx(expected, rel=0.02)


def test_higher_volatility_widens_the_spread():
    low = simulate_paths(10_000, 0, 8, 5, years=5, n_sims=5000, seed=3)[:, -1]
    high = simulate_paths(10_000, 0, 8, 30, years=5, n_sims=5000, seed=3)[:, -1]
    assert high.std() > low.std()


def test_lower_target_is_more_likely():
    paths = simulate_paths(10_000, 300, 8, 18, years=8, n_sims=3000)
    assert probability_of_goal(paths, 20_000) >= probability_of_goal(paths, 60_000)


def test_goal_already_met_is_certain_without_randomness():
    paths = simulate_paths(10_000, 0, 5, 0, years=2, n_sims=10)
    assert probability_of_goal(paths, 5_000) == 1.0
    assert probability_of_goal(paths, 1_000_000) == 0.0


def test_percentiles_are_ordered():
    paths = simulate_paths(10_000, 200, 8, 18, years=5, n_sims=2000)
    p = outcome_percentiles(paths)
    assert p[10] <= p[50] <= p[90]
    bands = percentile_bands(paths)
    assert (bands["p10"] <= bands["p50"]).all()
    assert (bands["p50"] <= bands["p90"]).all()
    assert len(bands) == paths.shape[1]


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        simulate_paths(1000, 0, 8, 15, years=0)
    with pytest.raises(ValueError):
        simulate_paths(1000, 0, 8, 15, years=1, n_sims=0)


def _synthetic_prices(n=300, seed=0, daily_vol=0.01):
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0004, daily_vol, size=n)
    return pd.Series(100 * np.cumprod(1 + returns), index=pd.bdate_range("2024-01-01", periods=n))


def test_portfolio_volatility_of_one_asset_matches_direct_calc():
    s = _synthetic_prices()
    df = pd.DataFrame({"AAA": s})
    expected = s.pct_change().dropna().std() * np.sqrt(252) * 100
    assert portfolio_volatility(df, {"AAA": 1.0}) == pytest.approx(expected)


def test_identical_assets_do_not_diversify():
    s = _synthetic_prices()
    df = pd.DataFrame({"AAA": s, "BBB": s})
    single = portfolio_volatility(df[["AAA"]], {"AAA": 1.0})
    both = portfolio_volatility(df, {"AAA": 0.5, "BBB": 0.5})
    assert both == pytest.approx(single)


def test_uncorrelated_assets_reduce_volatility():
    df = pd.DataFrame({"AAA": _synthetic_prices(seed=1), "BBB": _synthetic_prices(seed=2)})
    single = portfolio_volatility(df[["AAA"]], {"AAA": 1.0})
    mixed = portfolio_volatility(df, {"AAA": 0.5, "BBB": 0.5})
    assert mixed < single


def test_volatility_returns_none_without_enough_data():
    df = pd.DataFrame({"AAA": _synthetic_prices(n=20)})
    assert portfolio_volatility(df, {"AAA": 1.0}) is None
    assert portfolio_volatility(pd.DataFrame(), {"AAA": 1.0}) is None
    assert portfolio_volatility(_synthetic_prices().to_frame("AAA"), {"ZZZ": 1.0}) is None
