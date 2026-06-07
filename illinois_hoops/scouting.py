"""Opponent scouting engine.

Turns one-row-per-game data into a coach-ready profile of any team: their
four-factor identity on both ends, tempo, how they hold up against quality
opposition, recent form, and an auto-generated set of "keys to the game".

The four factors (Dean Oliver) are the backbone of basketball analytics:
shooting (eFG%), turnovers (TO%), rebounding (ORB%) and free throws (FTRate).
We grade a team on all four, on offence and defence, as national percentiles
so a coach instantly sees where the edges are.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import POWER_CONFS

# Reference populations the percentiles can be measured against.
# key -> (label, short description for the UI).
COMPARE_MODES = {
    "power": "High-major conferences",
    "national": "All of Division I",
    "tier": "Similar level (by ranking)",
}

# Each factor: (column, higher_is_better) from the team's own perspective.
_OFF_FACTORS = {
    "eFG%": ("off_efg", True),
    "TO%": ("off_to", False),
    "ORB%": ("off_orb", True),
    "FTRate": ("off_ftr", True),
}
# Defensive factors describe what the team *allows*; lower opp shooting/ORB/FTR
# is good, higher forced TO% is good.
_DEF_FACTORS = {
    "eFG%": ("def_efg", False),
    "TO%": ("def_to", True),
    "ORB%": ("def_orb", False),
    "FTRate": ("def_ftr", False),
}


def team_season_table(games: pd.DataFrame) -> pd.DataFrame:
    """Aggregate game rows to a team-season table of average four factors,
    efficiency and tempo. Used as the percentile reference population."""
    agg = (
        games.groupby("team")
        .agg(
            games=("date", "count"),
            conf=("conf", "first"),
            off_rtg=("off_rtg", "mean"),
            def_rtg=("def_rtg", "mean"),
            tempo=("tempo", "mean"),
            off_efg=("off_efg", "mean"),
            off_to=("off_to", "mean"),
            off_orb=("off_orb", "mean"),
            off_ftr=("off_ftr", "mean"),
            def_efg=("def_efg", "mean"),
            def_to=("def_to", "mean"),
            def_orb=("def_orb", "mean"),
            def_ftr=("def_ftr", "mean"),
        )
        .reset_index()
    )
    agg["net_rtg"] = agg["off_rtg"] - agg["def_rtg"]
    return agg


def _percentile(value: float, population: pd.Series, higher_is_better: bool) -> float:
    pct = (population < value).mean() * 100
    return round(pct if higher_is_better else 100 - pct, 0)


def reference_population(season: pd.DataFrame, team: str, compare: str) -> pd.DataFrame:
    """Subset of teams to measure ``team``'s percentiles against.

    ``compare`` is one of ``COMPARE_MODES``:
      * ``national`` — all of Division I (~365 teams).
      * ``power``    — high-major conferences only (ACC/B10/B12/SEC/BE, ~79).
      * ``tier``     — teams in the same net-rating quartile (similar overall level).
    The scouted team is always kept in the population so its own percentile is
    well-defined even when it sits outside the chosen group.
    """
    if compare == "power":
        ref = season[season["conf"].isin(POWER_CONFS)]
    elif compare == "tier":
        q = pd.qcut(season["net_rtg"], 4, labels=False, duplicates="drop")
        team_q = q[season["team"] == team].iloc[0]
        ref = season[q == team_q]
    else:  # national
        ref = season
    if team not in set(ref["team"]):
        ref = pd.concat([ref, season[season["team"] == team]], ignore_index=True)
    return ref


def team_profile(games: pd.DataFrame, team: str, compare: str = "power") -> dict:
    """Build a full scouting profile for ``team``.

    Percentiles are measured against the population chosen by ``compare`` (see
    :func:`reference_population`); defaults to high-major conferences.
    """
    season = team_season_table(games)
    if team not in set(season["team"]):
        raise ValueError(f"No game data for {team}")
    row = season.set_index("team").loc[team]
    ref = reference_population(season, team, compare)

    def factor_block(factors: dict) -> dict:
        out = {}
        for label, (col, hib) in factors.items():
            out[label] = {
                "value": round(float(row[col]), 1),
                "pct": _percentile(row[col], ref[col], hib),
            }
        return out

    offense = factor_block(_OFF_FACTORS)
    defense = factor_block(_DEF_FACTORS)

    # Splits and context from the team's own game log.
    log = games[games["team"] == team].copy()
    home = log[log["venue"] == "H"]
    away = log[log["venue"] == "A"]
    quality = log[log["adj_margin"].notna()]
    vs_good = log[log["opp_conf"].isin(["B10", "B12", "SEC", "ACC", "BE"])]
    recent = log.tail(10)

    return {
        "team": team,
        "record": f"{int(log['won'].sum())}-{int((~log['won']).sum())}",
        "off_rtg": round(float(row["off_rtg"]), 1),
        "def_rtg": round(float(row["def_rtg"]), 1),
        "net_rtg": round(float(row["net_rtg"]), 1),
        "tempo": round(float(row["tempo"]), 1),
        "tempo_pct": _percentile(row["tempo"], ref["tempo"], True),
        "compare": compare,
        "compare_label": COMPARE_MODES.get(compare, compare),
        "n_ref": int(len(ref)),
        "offense": offense,
        "defense": defense,
        "home_net": round(float((home["off_rtg"] - home["def_rtg"]).mean()), 1) if len(home) else None,
        "away_net": round(float((away["off_rtg"] - away["def_rtg"]).mean()), 1) if len(away) else None,
        "vs_power_record": f"{int(vs_good['won'].sum())}-{int((~vs_good['won']).sum())}" if len(vs_good) else "0-0",
        "recent_form": f"{int(recent['won'].sum())}-{int((~recent['won']).sum())} (last {len(recent)})",
        "log": log,
        "season_table": season,
    }


def scouting_report(profile: dict, n: int = 3) -> dict:
    """Generate human-readable strengths, weaknesses, and keys to the game.

    Strengths = top factors by percentile; weaknesses = bottom factors. Keys to
    the game translate the opponent's weaknesses into a game plan.
    """
    items = []
    for side, block in (("OFF", profile["offense"]), ("DEF", profile["defense"])):
        for label, d in block.items():
            items.append((side, label, d["pct"], d["value"]))

    strengths = sorted(items, key=lambda x: -x[2])[:n]
    weaknesses = sorted(items, key=lambda x: x[2])[:n]

    # Translate weaknesses into a tactical key.
    keys = []
    plays = {
        ("OFF", "eFG%"): "Run them off the 3-point line and contest at the rim — they don't shoot it well.",
        ("OFF", "TO%"): "Pressure the ball and trap ball screens; they are turnover-prone.",
        ("OFF", "ORB%"): "We can leak out — they don't crash the offensive glass.",
        ("OFF", "FTRate"): "They settle for jumpers and rarely get to the line; play aggressive defense.",
        ("DEF", "eFG%"): "Attack them in the half court — they give up efficient shots.",
        ("DEF", "TO%"): "Take care of the ball and they won't generate easy transition; they don't force turnovers.",
        ("DEF", "ORB%"): "Crash the offensive glass hard — they are a poor defensive rebounding team.",
        ("DEF", "FTRate"): "Drive the ball and draw fouls — they foul a lot.",
    }
    for side, label, pct, _ in weaknesses:
        if (side, label) in plays:
            keys.append(plays[(side, label)])

    return {
        "strengths": [f"{_fmt(s)} ({s[2]:.0f}th pct)" for s in strengths],
        "weaknesses": [f"{_fmt(w)} ({w[2]:.0f}th pct)" for w in weaknesses],
        "keys_to_game": keys,
    }


def _fmt(item) -> str:
    side, label, pct, value = item
    side_txt = "Offensive" if side == "OFF" else "Defensive"
    return f"{side_txt} {label} = {value}"


# Stats carried on each player card.
_PLAYER_CARD_COLS = ["player", "class", "position", "ppg", "porpag", "dporpag",
                     "usage", "ts", "drb_pct", "stl_pct", "blk_pct"]


def key_players(players: pd.DataFrame, team: str, n: int = 2,
                min_minutes: float = 40.0) -> dict:
    """Top ``n`` offensive (by PORPAG) and defensive (by D-PORPAG) players.

    Restricted to rotation players (>=``min_minutes``% of minutes) so tiny-sample
    bench guys don't top the list; falls back to the whole roster if needed.
    """
    pool = players[(players["team"] == team) & (players["min_pct"] >= min_minutes)]
    if len(pool) < n:
        pool = players[players["team"] == team]
    cols = [c for c in _PLAYER_CARD_COLS if c in pool.columns]

    def top(stat: str) -> list[dict]:
        return pool.sort_values(stat, ascending=False).head(n)[cols].to_dict("records")

    return {"offense": top("porpag"), "defense": top("dporpag")}
