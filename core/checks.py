"""
Sanity checks on user-entered holdings. No Streamlit dependency, so unit-testable.
"""


def currency_mismatches(holdings: list) -> list[tuple]:
    """
    Holdings whose currency doesn't match what the data provider says they trade in.

    Returns (holding, reported_currency) pairs. Holdings with no reported currency
    (offline, unknown ticker) are skipped, since there is nothing to compare.
    """
    out = []
    for h in holdings:
        reported = (h.reported_currency or "").strip()
        if reported and reported.upper() != h.currency.upper():
            out.append((h, reported.upper()))
    return out


def usable_rate(value) -> bool:
    """A plausible exchange rate: a positive number that isn't wildly off."""
    try:
        return 0.05 < float(value) < 20
    except (TypeError, ValueError):
        return False
