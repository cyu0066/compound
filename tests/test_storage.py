"""
Tests for saving and loading data bundles (core/storage.py).
Run with: pytest
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.models import Holding, Goal, WatchlistItem
from core.storage import bundle_to_json, bundle_from_json_str, targets_from_json_str


def _sample():
    holdings = [Holding(name="Apple", ticker="AAPL", shares=2, currency="USD", manual_price=100.0)]
    goals = [Goal(name="Test", target_amount=1000, years=2)]
    watchlist = [WatchlistItem(ticker="TSLA")]
    return holdings, goals, watchlist


def test_targets_round_trip():
    packed = bundle_to_json(*_sample(), targets={"AAPL": 60.0, "IVV.AX": 40.0})
    assert targets_from_json_str(packed) == {"AAPL": 60.0, "IVV.AX": 40.0}


def test_bundle_without_targets_still_loads():
    packed = bundle_to_json(*_sample())
    assert targets_from_json_str(packed) == {}
    holdings, goals, watchlist = bundle_from_json_str(packed)
    assert holdings[0].ticker == "AAPL" and goals[0].name == "Test" and watchlist[0].ticker == "TSLA"


def test_old_files_without_a_targets_key_still_load():
    old_format = json.dumps({"holdings": [], "goals": [], "watchlist": []})
    assert targets_from_json_str(old_format) == {}
    assert bundle_from_json_str(old_format) == ([], [], [])
