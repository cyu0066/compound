"""
Rebalancing suggestions: given target weights, work out what to buy or sell.

Two modes:
  * buy-only (allow_sells=False): put new cash into the most underweight
    holdings and never sell. Avoids realising gains, so it suits regular
    contributions.
  * full rebalance (allow_sells=True): move every holding to its target,
    selling overweight positions and buying underweight ones.

No Streamlit dependency, so it is unit-testable on its own.
"""
from typing import Optional

import pandas as pd

WEIGHT_SUM_TOLERANCE = 0.05  # percentage points


def current_weights_pct(values: dict) -> dict:
    """Current allocation as percentages (0-100) from {ticker: value}."""
    total = sum(v for v in values.values() if v and v > 0)
    if total <= 0:
        return {t: 0.0 for t in values}
    return {t: (v / total * 100 if v and v > 0 else 0.0) for t, v in values.items()}


def equal_weights_pct(tickers: list) -> dict:
    """Equal target weights that sum to exactly 100."""
    if not tickers:
        return {}
    w = round(100 / len(tickers), 1)
    weights = {t: w for t in tickers}
    weights[tickers[0]] = round(weights[tickers[0]] + (100 - sum(weights.values())), 1)
    return weights


def round_weights_to_100(weights: dict, decimals: int = 1) -> dict:
    """Round weights, putting any rounding leftover on the largest one so they sum to 100."""
    if not weights:
        return {}
    rounded = {t: round(w, decimals) for t, w in weights.items()}
    leftover = round(100 - sum(rounded.values()), decimals)
    largest = max(rounded, key=rounded.get)
    rounded[largest] = round(rounded[largest] + leftover, decimals)
    return rounded


def validate_targets(targets_pct: dict) -> None:
    total = sum(targets_pct.values())
    if any(v < 0 for v in targets_pct.values()):
        raise ValueError("Target weights cannot be negative.")
    if abs(total - 100) > WEIGHT_SUM_TOLERANCE:
        raise ValueError(f"Target weights add up to {total:.2f}%, not 100%.")


def rebalance_plan(
    current_values: dict,
    targets_pct: dict,
    new_cash: float = 0.0,
    allow_sells: bool = False,
    tolerance_pct: float = 0.0,
    prices: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Build a trade plan, all in AUD.

    current_values: {ticker: current value in AUD}
    targets_pct:    {ticker: target weight, summing to 100}
    new_cash:       extra cash being added to the portfolio
    allow_sells:    False = buy-only plan; True = full rebalance
    tolerance_pct:  holdings within this many percentage points of target are left alone
    prices:         optional {ticker: AUD price per share} to estimate share counts

    Returns one row per ticker with current/target weights, the trade in AUD
    (positive = buy, negative = sell), an action and, if prices are given,
    approximate shares.
    """
    if new_cash < 0:
        raise ValueError("new_cash cannot be negative.")
    validate_targets(targets_pct)

    tickers = list(dict.fromkeys(list(current_values) + list(targets_pct)))
    current = {t: max(current_values.get(t, 0.0) or 0.0, 0.0) for t in tickers}
    targets = {t: targets_pct.get(t, 0.0) for t in tickers}

    total_now = sum(current.values())
    total_after = total_now + new_cash
    current_pct = {t: (current[t] / total_now * 100 if total_now > 0 else 0.0) for t in tickers}

    target_value = {t: targets[t] / 100 * total_after for t in tickers}
    trade = {t: target_value[t] - current[t] for t in tickers}

    # Leave holdings that are already close to target alone.
    if tolerance_pct > 0 and total_now > 0:
        for t in tickers:
            if abs(current_pct[t] - targets[t]) <= tolerance_pct:
                trade[t] = 0.0

    if not allow_sells:
        buys = {t: max(trade[t], 0.0) for t in tickers}
        total_buys = sum(buys.values())
        # Spend the new cash across underweight holdings in proportion to how far
        # under target they are. Never spend more than the cash available.
        scale = min(new_cash / total_buys, 1.0) if total_buys > 0 else 0.0
        trade = {t: buys[t] * scale for t in tickers}

    rows = []
    for t in tickers:
        amount = trade[t]
        if abs(amount) < 0.005:
            action = "Hold"
            amount = 0.0
        else:
            action = "Buy" if amount > 0 else "Sell"
        row = {
            "Ticker": t,
            "Current value (AUD)": current[t],
            "Current %": current_pct[t],
            "Target %": targets[t],
            "Drift (pp)": current_pct[t] - targets[t],
            "Action": action,
            "Trade (AUD)": amount,
            "Value after (AUD)": current[t] + amount,
        }
        if prices is not None:
            price = prices.get(t)
            row["Approx. shares"] = (amount / price) if price and price > 0 else None
        rows.append(row)

    df = pd.DataFrame(rows)
    return df.sort_values("Drift (pp)", ascending=False, ignore_index=True)
