"""
Monte Carlo goal simulation.

Instead of projecting one smooth line at a fixed return, simulate thousands of
possible futures where each month's return is random, then report how often a
goal is reached. No Streamlit dependency, so it is unit-testable on its own.

Model: monthly growth multipliers are lognormal,

    log(multiplier) ~ Normal((mu - sigma^2 / 2) / 12, sigma^2 / 12)

where mu is the expected annual return and sigma is annual volatility. The
drift correction (-sigma^2 / 2) makes the *expected* multiplier exactly
exp(mu / 12), so the average simulated outcome matches the assumed return
while individual paths spread out around it. A contribution is added at the
end of each month, as in the deterministic projection.
"""
from typing import Optional

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252
MIN_HISTORY_ROWS = 60


def simulate_paths(
    present_value: float,
    monthly_contribution: float,
    annual_return_pct: float,
    annual_vol_pct: float,
    years: float,
    n_sims: int = 5000,
    seed: Optional[int] = 42,
) -> np.ndarray:
    """
    Simulate portfolio balances month by month.

    Returns an array of shape (n_sims, months + 1); column 0 is the starting
    value. A fixed default seed keeps results stable between app reruns.
    """
    months = int(round(years * 12))
    if months < 1:
        raise ValueError("years must cover at least one month")
    if n_sims < 1:
        raise ValueError("n_sims must be positive")

    mu = annual_return_pct / 100
    sigma = max(annual_vol_pct, 0.0) / 100

    rng = np.random.default_rng(seed)
    monthly_drift = (mu - 0.5 * sigma**2) / 12
    monthly_sd = sigma / np.sqrt(12)
    log_growth = rng.normal(monthly_drift, monthly_sd, size=(n_sims, months))
    multipliers = np.exp(log_growth)

    paths = np.empty((n_sims, months + 1))
    paths[:, 0] = present_value
    for m in range(1, months + 1):
        paths[:, m] = paths[:, m - 1] * multipliers[:, m - 1] + monthly_contribution
    return paths


def probability_of_goal(paths: np.ndarray, target: float, months: Optional[int] = None) -> float:
    """Share of simulated paths at or above `target` after `months` (default: the end)."""
    col = paths.shape[1] - 1 if months is None else min(int(months), paths.shape[1] - 1)
    return float(np.mean(paths[:, col] >= target))


def outcome_percentiles(
    paths: np.ndarray, months: Optional[int] = None, percentiles=(10, 50, 90)
) -> dict:
    """Percentile outcomes (e.g. 10th/50th/90th) at a given month."""
    col = paths.shape[1] - 1 if months is None else min(int(months), paths.shape[1] - 1)
    values = np.percentile(paths[:, col], percentiles)
    return {int(p): float(v) for p, v in zip(percentiles, values)}


def percentile_bands(paths: np.ndarray, percentiles=(10, 50, 90)) -> pd.DataFrame:
    """Percentile balance for every month, for drawing a fan chart."""
    data = {f"p{int(p)}": np.percentile(paths, p, axis=0) for p in percentiles}
    df = pd.DataFrame(data)
    df.insert(0, "month", np.arange(paths.shape[1]))
    return df


def portfolio_volatility(price_history: pd.DataFrame, weights: dict) -> Optional[float]:
    """
    Annualised volatility (%) of a portfolio, estimated from daily prices.

    price_history: DataFrame, one column of daily closes per ticker.
    weights: {ticker: weight}; weights are re-normalised over tickers that
        actually have history.

    Assumes constant weights (daily-rebalanced) and ignores currency moves, so
    treat it as an estimate. Returns None if there is too little data.
    """
    tickers = [t for t in weights if t in price_history.columns and weights[t] > 0]
    if not tickers:
        return None

    prices = price_history[tickers].sort_index().ffill().dropna()
    if len(prices) < MIN_HISTORY_ROWS:
        return None

    w = pd.Series({t: weights[t] for t in tickers}, dtype=float)
    w = w / w.sum()

    daily_returns = prices.pct_change().dropna()
    if len(daily_returns) < MIN_HISTORY_ROWS - 1:
        return None

    portfolio_returns = (daily_returns * w).sum(axis=1)
    return float(portfolio_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100)
