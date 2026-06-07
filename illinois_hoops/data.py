"""Data layer for the Illinois Hoops Analytics Hub.

All data comes from BartTorvik (https://barttorvik.com), which publishes
opponent-adjusted college-basketball metrics for free. We hit three public
endpoints and cache the raw responses to ``data/raw`` so the app works offline
and we are polite to Torvik's servers:

* ``getadvstats.php``      -> player-season advanced stats (PORPAG, usage, ...)
* ``{year}_team_results``  -> team-season adjusted efficiency, four factors
* ``getgamestats.php``     -> one row per team per game (for scouting)

Column positions were reverse-engineered and validated against known players
and teams (see notebooks/01_validate_columns.py). Only the columns we trust
are named; the rest are dropped.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pandas as pd
import requests

from .config import DEFAULT_SEASON, bucket_position

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_HEADERS = {"User-Agent": "Mozilla/5.0 (Illinois-Hoops-Analytics; educational project)"}
_TIMEOUT = 40


# --------------------------------------------------------------------------- #
# Low-level fetch + cache
# --------------------------------------------------------------------------- #
def _cached_get(url: str, cache_name: str, refresh: bool = False) -> str:
    """GET ``url`` with on-disk caching. Returns the raw response text."""
    cache_file = CACHE_DIR / cache_name
    if cache_file.exists() and not refresh:
        return cache_file.read_text()
    resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    text = resp.text
    if "Verifying Browser" in text[:300]:
        raise RuntimeError(f"BartTorvik anti-bot wall hit for {url}")
    cache_file.write_text(text)
    return text


# --------------------------------------------------------------------------- #
# Players
# --------------------------------------------------------------------------- #
# Confirmed column positions from getadvstats.php (67 columns, no header).
# Positions were validated against BartTorvik's own labelled team table (every
# value matched for Kylan Boswell and Bishop Boswell). The advanced "plus-minus"
# family (bpm/obpm/dbpm) is only meaningful with a minutes filter — it inflates
# wildly for tiny-minute players — so handle it with care downstream.
_PLAYER_COLS = {
    0: "player", 1: "team", 2: "conf", 3: "games", 4: "min_pct", 5: "ortg",
    6: "usage", 7: "efg", 8: "ts", 9: "orb_pct", 10: "drb_pct", 11: "ast_pct",
    12: "to_pct", 13: "ftm", 14: "fta", 15: "ft_pct", 16: "fg2m", 17: "fg2a",
    18: "fg2_pct", 19: "fg3m", 20: "fg3a", 21: "fg3_pct", 22: "blk_pct",
    23: "stl_pct", 24: "ftr", 25: "class", 26: "height", 27: "number",
    28: "porpag", 30: "fouls_per40", 31: "season", 32: "pid", 33: "hometown",
    35: "ast_to",
    # Shot profile ("shot diet"): rim attempts, mid-range, and 3PT volume.
    # Validated against BartTorvik's labelled table for two players.
    36: "rim_m", 37: "rim_a", 40: "rim_pct",
    38: "mid_m", 39: "mid_a", 41: "mid_pct",
    65: "fg3_per100",
    47: "drtg", 48: "dporpag", 53: "bpm", 55: "obpm", 56: "dbpm",
    59: "rpg", 60: "apg", 63: "ppg", 64: "position", 66: "dob",
}


def fetch_players(year: int = DEFAULT_SEASON, refresh: bool = False) -> pd.DataFrame:
    """Player-season advanced stats for the whole of D-I."""
    text = _cached_get(
        f"https://barttorvik.com/getadvstats.php?year={year}&csv=1",
        f"{year}_players.csv", refresh,
    )
    rows = list(csv.reader(io.StringIO(text)))
    records = []
    for r in rows:
        if len(r) < 67:
            continue
        rec = {name: r[i] for i, name in _PLAYER_COLS.items()}
        records.append(rec)
    df = pd.DataFrame(records)

    numeric = [
        "games", "min_pct", "ortg", "usage", "efg", "ts", "orb_pct", "drb_pct",
        "ast_pct", "to_pct", "ftm", "fta", "ft_pct", "fg2m", "fg2a", "fg2_pct",
        "fg3m", "fg3a", "fg3_pct", "blk_pct", "stl_pct", "ftr", "porpag",
        "fouls_per40", "ast_to", "drtg", "dporpag", "bpm", "obpm", "dbpm",
        "rpg", "apg", "ppg",
        "rim_m", "rim_a", "rim_pct", "mid_m", "mid_a", "mid_pct", "fg3_per100",
    ]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # total rebounding = offensive + defensive rebound rate (both ends)
    df["reb_pct"] = df["orb_pct"].fillna(0) + df["drb_pct"].fillna(0)
    # jump-shooting eFG% = efficiency on shots away from the rim (mid-range 2s +
    # threes, threes weighted 1.5x). Isolates perimeter touch from rim scoring,
    # so "shooting" doesn't just mirror "scoring". NaN below 10 attempts (sample).
    _ja = df["mid_a"].fillna(0) + df["fg3a"].fillna(0)
    _jm = df["mid_m"].fillna(0) + 1.5 * df["fg3m"].fillna(0)
    df["jump_efg"] = (_jm / _ja.where(_ja >= 10) * 100).round(1)
    df["pos_bucket"] = df["position"].map(bucket_position)
    df["height_in"] = df["height"].map(_height_to_inches)
    df["season"] = year
    return df


def _height_to_inches(h: str) -> float | None:
    try:
        feet, inches = str(h).split("-")
        return int(feet) * 12 + int(inches)
    except (ValueError, AttributeError):
        return None


# --------------------------------------------------------------------------- #
# Teams
# --------------------------------------------------------------------------- #
# Confirmed column positions from {year}_team_results.json (45 columns).
_TEAM_COLS = {
    0: "rank", 1: "team", 2: "conf", 3: "record", 4: "adj_oe", 5: "adj_oe_rank",
    6: "adj_de", 7: "adj_de_rank", 8: "barthag", 10: "wins", 11: "losses",
    14: "conf_record", 44: "adj_tempo",
}


def fetch_teams(year: int = DEFAULT_SEASON, refresh: bool = False) -> pd.DataFrame:
    """Team-season adjusted efficiency and rankings."""
    text = _cached_get(
        f"https://barttorvik.com/{year}_team_results.json",
        f"{year}_teams.json", refresh,
    )
    data = json.loads(text)
    records = [{name: row[i] for i, name in _TEAM_COLS.items()} for row in data]
    df = pd.DataFrame(records)
    for col in ["rank", "adj_oe", "adj_oe_rank", "adj_de", "adj_de_rank",
                "barthag", "wins", "losses", "adj_tempo"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["net_rtg"] = df["adj_oe"] - df["adj_de"]
    df["season"] = year
    return df


# --------------------------------------------------------------------------- #
# Games
# --------------------------------------------------------------------------- #
# Confirmed column positions from getgamestats.php (31 columns).
# Offensive four factors (cols 10-13) are the team's own; defensive four
# factors (cols 15-18) are what the opponent managed (i.e. what we allowed).
_GAME_COLS = {
    0: "date", 2: "team", 3: "conf", 4: "opponent", 5: "venue", 6: "result",
    7: "off_rtg", 8: "def_rtg",
    10: "off_efg", 11: "off_to", 12: "off_orb", 13: "off_ftr",
    15: "def_efg", 16: "def_to", 17: "def_orb", 18: "def_ftr",
    20: "opp_conf", 23: "tempo", 25: "coach", 26: "opp_coach",
    27: "adj_margin",
}

# Column 31 (index 29) is a JSON box score for both teams. Within each team's
# 15-value block the order is FGM, FGA, 3PM, 3PA, FTM, FTA, ORB, DRB, TRB, AST,
# STL, BLK, TO, PF, PTS. We pull the team's own assists / steals / blocks /
# fouls — "style" stats the four factors don't capture.
_BOX_OFFSET = {"ast": 9, "stl": 10, "blk": 11, "pf": 13}


def _parse_box(raw_row: list[str]) -> dict:
    """Extract the row team's own box-score style stats from column 29."""
    try:
        box = json.loads(raw_row[29])
        own = raw_row[2]
        if box[2] == own:          # team listed first
            start = 4
        elif box[3] == own:        # team listed second
            start = 19
        else:
            return {}
        block = box[start:start + 15]
        return {k: block[off] for k, off in _BOX_OFFSET.items()}
    except (IndexError, ValueError, TypeError):
        return {}


def fetch_games(year: int = DEFAULT_SEASON, refresh: bool = False) -> pd.DataFrame:
    """One row per team per game, with four-factor splits."""
    text = _cached_get(
        f"https://barttorvik.com/getgamestats.php?year={year}&csv=1",
        f"{year}_games.csv", refresh,
    )
    rows = list(csv.reader(io.StringIO(text)))
    records = []
    for r in rows:
        if len(r) < 28:
            continue
        rec = {name: r[i] for i, name in _GAME_COLS.items()}
        rec.update(_parse_box(r))   # adds ast / stl / blk / pf when available
        records.append(rec)
    df = pd.DataFrame(records)
    numeric = ["off_rtg", "def_rtg", "off_efg", "off_to", "off_orb", "off_ftr",
               "def_efg", "def_to", "def_orb", "def_ftr", "tempo", "adj_margin",
               "ast", "stl", "blk", "pf"]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["won"] = df["result"].str.startswith("W")
    df["season"] = year
    return df


if __name__ == "__main__":
    # Smoke test the whole data layer.
    p = fetch_players()
    t = fetch_teams()
    g = fetch_games()
    print(f"players: {len(p):>5}  cols={list(p.columns)[:8]}...")
    print(f"teams:   {len(t):>5}  cols={list(t.columns)[:8]}...")
    print(f"games:   {len(g):>5}  cols={list(g.columns)[:8]}...")
    print("\nIllinois roster sample:")
    print(p[p.team == "Illinois"][["player", "class", "pos_bucket", "usage", "porpag"]].to_string(index=False))
