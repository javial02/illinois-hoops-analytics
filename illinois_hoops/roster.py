"""Roster construction & fit module.

Public data does not expose reliable five-man-unit (lineup) data for college
basketball, so rather than fake it we tackle the question a GM actually asks in
the portal era: *what does my roster look like, where are the holes, and how
does a given target change the picture?*

This module profiles a team's (returning) roster across the six skill
dimensions used elsewhere in the app, benchmarked as percentiles against
high-major rotation players, and lets you simulate adding a transfer target to
see the before/after fit.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import POWER_CONFS
from .portal import SKILL_COLS, _LOWER_IS_BETTER

# Reference player pools the skill percentiles can be measured against.
# (Team-level "similar tier" doesn't map to individual players, so the player
# chart offers high-major vs all-D-I rotation only.)
SKILL_COMPARE_MODES = {
    "power": "High-major rotation",
    "national": "All-D-I rotation",
}

DISPLAY_COLS = [
    "player", "class", "position", "pos_bucket", "height", "min_pct",
    "usage", "porpag", "ts", "fg3_pct", "ast_pct", "drb_pct", "blk_pct",
]


def get_roster(players: pd.DataFrame, team: str, departing: set[str] | None = None) -> pd.DataFrame:
    """Returning roster for ``team`` (seniors assumed departing by default)."""
    roster = players[players["team"] == team].copy()
    if departing is None:
        departing = set(roster.loc[roster["class"] == "Sr", "player"])
    roster["status"] = np.where(roster["player"].isin(departing), "Departing", "Returning")
    return roster.sort_values(["status", "min_pct"], ascending=[True, False])


def _baseline(players: pd.DataFrame, compare: str = "power") -> pd.DataFrame:
    """Rotation players (>=40% minutes) used as the percentile reference.

    ``compare="power"`` restricts to high-major conferences (the level we
    compete at); ``"national"`` uses rotation players across all of D-I.
    """
    pool = players[players["min_pct"] >= 40]
    if compare == "power":
        pool = pool[pool["conf"].isin(POWER_CONFS)]
    return pool


def skill_percentiles(row: pd.Series, baseline: pd.DataFrame) -> dict:
    """Percentile of a single player on each skill vs the high-major baseline."""
    out = {}
    for skill, col in SKILL_COLS.items():
        pop = baseline[col].dropna()
        val = row.get(col)
        if pd.isna(val) or pop.empty:
            out[skill] = 50.0
            continue
        pct = (pop < val).mean() * 100
        out[skill] = round(100 - pct if skill in _LOWER_IS_BETTER else pct, 0)
    return out


def roster_profile(players: pd.DataFrame, team: str, departing: set[str] | None = None,
                   compare: str = "power", arrivals: set[str] | None = None) -> dict:
    """Minutes-weighted skill profile of the projected roster (percentiles).

    The projected roster is returning − departing + ``arrivals`` (simulated
    incoming signings from other teams).
    """
    roster = get_roster(players, team, departing)
    returning = roster[roster["status"] == "Returning"].copy()
    if arrivals:
        arr = players[(players["player"].isin(arrivals)) & (players["team"] != team)]
        arr = arr.sort_values("min_pct", ascending=False).drop_duplicates("player")
        returning = pd.concat([returning, arr], ignore_index=True)
    baseline = _baseline(players, compare)

    w = (returning["min_pct"].fillna(0) * returning["games"].fillna(0)).to_numpy()
    if w.sum() == 0:
        w = np.ones(len(returning))

    profile = {}
    for skill, col in SKILL_COLS.items():
        pop = baseline[col].dropna()
        vals = returning[col].to_numpy(dtype=float)
        ok = ~np.isnan(vals)
        if not ok.any() or pop.empty:
            profile[skill] = 50.0
            continue
        team_val = np.average(vals[ok], weights=w[ok])
        pct = (pop < team_val).mean() * 100
        profile[skill] = round(100 - pct if skill in _LOWER_IS_BETTER else pct, 0)

    # Minutes share by position bucket among returners.
    pos_share = {}
    total = w.sum()
    for bucket in ["Guard", "Wing", "Forward", "Big"]:
        mask = (returning["pos_bucket"] == bucket).to_numpy()
        pos_share[bucket] = round(w[mask].sum() / total * 100, 0) if total else 0

    return {"skill_profile": profile, "pos_share": pos_share, "returning": returning,
            "compare": compare, "compare_label": SKILL_COMPARE_MODES.get(compare, compare),
            "n_ref": int(len(baseline))}


def simulate_addition(players: pd.DataFrame, team: str, target_player: str,
                      departing: set[str] | None = None, compare: str = "power") -> dict:
    """Recompute the roster profile as if ``target_player`` were added.

    Returns before/after skill profiles so the UI can show the delta.
    """
    before = roster_profile(players, team, departing, compare)
    target_rows = players[players["player"] == target_player]
    if target_rows.empty:
        return {"before": before["skill_profile"], "after": before["skill_profile"], "target": None}

    target = target_rows.iloc[0]
    augmented = pd.concat([before["returning"], target_rows], ignore_index=True)
    baseline = _baseline(players, compare)

    w = (augmented["min_pct"].fillna(0) * augmented["games"].fillna(0)).to_numpy()
    after = {}
    for skill, col in SKILL_COLS.items():
        pop = baseline[col].dropna()
        vals = augmented[col].to_numpy(dtype=float)
        ok = ~np.isnan(vals)
        team_val = np.average(vals[ok], weights=w[ok])
        pct = (pop < team_val).mean() * 100
        after[skill] = round(100 - pct if skill in _LOWER_IS_BETTER else pct, 0)

    return {
        "before": before["skill_profile"],
        "after": after,
        "target": target,
        "target_skills": skill_percentiles(target, baseline),
    }
