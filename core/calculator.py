"""
Currency conversion, portfolio valuation, and growth-projection maths.
No Streamlit dependency, so it's unit-testable and reusable on its own.
"""
from typing import Optional

import pandas as pd


def to_aud(amount: Optional[float], currency: str, aud_usd: float, aud_nzd: float) -> Optional[float]:
    """
    Convert an amount in AUD/USD/NZD to AUD.
    aud_usd: how many USD equal 1 AUD (e.g. 0.717 means 1 AUD = 0.717 USD)
    aud_nzd: how many NZD equal 1 AUD (e.g. 1.225 means 1 AUD = 1.225 NZD)
    """
    if amount is None:
        return None
    currency = currency.upper()
    if currency == "AUD":
        return amount
    if currency == "USD":
        return amount / aud_usd
    if currency == "NZD":
        return amount / aud_nzd
    raise ValueError(f"Unsupported currency: {currency}")


def portfolio_summary(holdings: list, aud_usd: float, aud_nzd: float) -> pd.DataFrame:
    """One row per holding, valued in AUD."""
    rows = []
    for h in holdings:
        value_aud = to_aud(h.value_native, h.currency, aud_usd, aud_nzd)
        rows.append({
            "Platform": h.platform,
            "Name": h.name,
            "Ticker": h.ticker,
            "Shares": h.shares,
            "Currency": h.currency,
            "Price (native)": h.price,
            "Price source": h.price_source,
            "Value (AUD)": value_aud,
        })
    return pd.DataFrame(rows)


def combine_by_ticker(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge rows for the same ticker held at different brokers into one row.

    Shares and value are added up and the brokers are listed together
    ("Broker A, Broker B"). Rows are only merged when the currency also matches,
    so a mistyped currency stays visible instead of being silently blended in.
    """
    if df.empty:
        return df

    def brokers(series) -> str:
        seen = []
        for b in series:
            b = (b or "").strip()
            if b and b not in seen:
                seen.append(b)
        return ", ".join(seen)

    return df.groupby(["Ticker", "Currency"], sort=False, as_index=False).agg(
        Platform=("Platform", brokers),
        Name=("Name", "first"),
        Shares=("Shares", "sum"),
        **{
            "Price (native)": ("Price (native)", "first"),
            "Price source": ("Price source", "first"),
            "Value (AUD)": ("Value (AUD)", lambda v: v.sum(min_count=1)),
        },
    )[["Platform", "Name", "Ticker", "Shares", "Currency", "Price (native)", "Price source", "Value (AUD)"]]


# ---------------------------------------------------------------------------
# Growth projection maths
# ---------------------------------------------------------------------------

def future_value(present_value: float, monthly_contribution: float,
                  annual_return_pct: float, years: float) -> float:
    """
    Future value of a lump sum + regular monthly contributions,
    compounded monthly (ordinary annuity, contribution at end of month).
    """
    r = (annual_return_pct / 100) / 12
    n = years * 12
    if r == 0:
        return present_value + monthly_contribution * n
    return present_value * (1 + r) ** n + monthly_contribution * (((1 + r) ** n - 1) / r)


def projection_series(present_value: float, monthly_contribution: float,
                       annual_return_pct: float, years: float) -> pd.DataFrame:
    """Month-by-month projected balance, for charting."""
    r = (annual_return_pct / 100) / 12
    months = int(years * 12)
    balance = present_value
    records = [{"month": 0, "value_aud": balance}]
    for m in range(1, months + 1):
        balance = balance * (1 + r) + monthly_contribution
        records.append({"month": m, "value_aud": balance})
    return pd.DataFrame(records)


def required_monthly_contribution(present_value: float, goal: float,
                                   annual_return_pct: float, years: float) -> float:
    """Monthly contribution needed to reach `goal` in `years`, given an assumed return."""
    r = (annual_return_pct / 100) / 12
    n = years * 12
    if n <= 0:
        return float("inf")
    if r == 0:
        return (goal - present_value) / n
    growth_of_lump_sum = present_value * (1 + r) ** n
    annuity_factor = ((1 + r) ** n - 1) / r
    return (goal - growth_of_lump_sum) / annuity_factor


def required_annual_return(present_value: float, goal: float,
                            monthly_contribution: float, years: float,
                            low: float = -50.0, high: float = 200.0,
                            tolerance: float = 1e-6) -> Optional[float]:
    """
    Annual return (%) needed to reach `goal` in `years`, given a fixed monthly
    contribution. Solved numerically (bisection) since there's no closed form.
    Returns None if the goal isn't reachable within the search range.
    """
    def f(rate_pct: float) -> float:
        return future_value(present_value, monthly_contribution, rate_pct, years) - goal

    if f(low) > 0:
        return low  # goal already reached even at the lowest return in range
    if f(high) < 0:
        return None  # not reachable even at a very high assumed return

    for _ in range(200):
        mid = (low + high) / 2
        if abs(f(mid)) < tolerance:
            return mid
        if f(mid) < 0:
            low = mid
        else:
            high = mid
    return (low + high) / 2
