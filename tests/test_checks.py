"""
Tests for the holding sanity checks (core/checks.py).
Run with: pytest
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.checks import currency_mismatches, usable_rate
from core.models import Holding


def _h(ticker, currency, reported):
    return Holding(name=ticker, ticker=ticker, shares=1, currency=currency, reported_currency=reported)


def test_flags_a_holding_entered_in_the_wrong_currency():
    wrong, right = _h("NVDA", "NZD", "USD"), _h("IVV.AX", "AUD", "AUD")
    assert currency_mismatches([wrong, right]) == [(wrong, "USD")]


def test_comparison_ignores_case():
    assert currency_mismatches([_h("V", "usd", "USD")]) == []


def test_unknown_currency_is_not_flagged():
    assert currency_mismatches([_h("USF.NZ", "NZD", None), _h("X", "AUD", "")]) == []


def test_usable_rate_rejects_nonsense():
    assert usable_rate(0.65) and usable_rate("1.12")
    assert not any(usable_rate(v) for v in (None, 0, -1, 500, "abc", float("nan")))
