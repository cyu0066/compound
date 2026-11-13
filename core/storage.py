"""
Loading the bundled example data, and JSON import/export so a user's
holdings/goals/watchlist can survive across browser sessions without a
database — download a file, re-upload it next time.
"""
import json
from pathlib import Path

from .models import Holding, Goal, WatchlistItem


def load_holdings(path: str | Path) -> list[Holding]:
    with open(path) as f:
        data = json.load(f)
    return [Holding(**h) for h in data.get("holdings", [])]


def load_goals(path: str | Path) -> list[Goal]:
    with open(path) as f:
        data = json.load(f)
    return [Goal(**g) for g in data.get("goals", [])]


def load_watchlist(path: str | Path) -> list[WatchlistItem]:
    with open(path) as f:
        data = json.load(f)
    return [WatchlistItem(ticker=w["ticker"], note=w.get("note", "")) for w in data.get("watchlist", [])]


def bundle_to_json(
    holdings: list[Holding],
    goals: list[Goal],
    watchlist: list[WatchlistItem],
    targets: dict | None = None,
) -> str:
    """Package everything into one downloadable JSON file."""
    return json.dumps({
        "holdings": [h.to_dict() for h in holdings],
        "goals": [g.to_dict() for g in goals],
        "watchlist": [w.to_dict() for w in watchlist],
        "targets": {t: float(v) for t, v in (targets or {}).items()},
    }, indent=2)


def targets_from_json_str(s: str) -> dict:
    """Target weights ({ticker: percent}) from an uploaded bundle; empty if none saved."""
    data = json.loads(s)
    return {str(t): float(v) for t, v in (data.get("targets") or {}).items()}


def bundle_from_json_str(s: str) -> tuple[list[Holding], list[Goal], list[WatchlistItem]]:
    """Parse an uploaded bundle back into model objects."""
    data = json.loads(s)
    holdings = [Holding(**h) for h in data.get("holdings", [])]
    goals = [Goal(**g) for g in data.get("goals", [])]
    watchlist = [WatchlistItem(ticker=w["ticker"], note=w.get("note", "")) for w in data.get("watchlist", [])]
    return holdings, goals, watchlist
