"""Transfer Portal Fit & Value engine — the flagship module.

A college GM building a roster through the transfer portal has two questions
about any candidate:

1. **Will the production translate?**  A player dominating a low-major league
   is not the same bet as one producing in the Big Ten. BartTorvik's PORPAG
   (Points Over Replacement Per Adjusted Game) is already *opponent-adjusted*,
   which is a strong starting point, but moving *up* a level still carries a
   well-documented "level-up tax". We model that explicitly.

2. **Does he fill a hole we actually have?**  A great wing is low priority if
   you return three wings and have no centre. We derive Illinois's positional
   and skill needs from the returning roster and score fit against them.

The output is a single, explainable ``target_score`` per candidate, with the
value and fit components kept separate so a coach can interrogate *why* a name
ranks where it does. Nothing here is a black box.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import POWER_CONFS

# --------------------------------------------------------------------------- #
# 1. Competition level → "will it translate up?" multiplier
# --------------------------------------------------------------------------- #
# We rank every conference by the average team strength (Barthag) of its
# members, then map onto a translation multiplier. The scale reflects the
# empirically observed retention of box-score value when a player steps up a
# level: roughly full retention for a lateral high-major move, down to ~60%
# for the lowest leagues. This is a deliberately transparent, defensible
# assumption rather than a hidden coefficient — a coach can see and challenge
# every number.
_TIER_MULTIPLIER = {
    1: 1.00,  # top tier (power conferences)
    2: 0.90,  # strong mids (e.g. A10, Mountain West, WCC, AAC)
    3: 0.80,  # solid mids
    4: 0.71,  # lower mids
    5: 0.63,  # lowest leagues
}


def conference_strength(teams: pd.DataFrame) -> pd.DataFrame:
    """Return a per-conference table with a strength tier (1=best..5=worst)."""
    grp = (
        teams.groupby("conf")
        .agg(avg_barthag=("barthag", "mean"), n_teams=("team", "count"))
        .reset_index()
    )
    # Power conferences are always tier 1 regardless of a down year; the rest
    # are split into four tiers by average Barthag.
    grp["is_power"] = grp["conf"].isin(POWER_CONFS)
    non_power = grp[~grp["is_power"]].copy()
    # qcut into 4 tiers (2..5), best Barthag -> tier 2.
    non_power["tier"] = pd.qcut(
        non_power["avg_barthag"], 4, labels=[5, 4, 3, 2]
    ).astype(int)
    grp = grp.merge(non_power[["conf", "tier"]], on="conf", how="left")
    grp.loc[grp["is_power"], "tier"] = 1
    grp["tier"] = grp["tier"].astype(int)
    grp["translation"] = grp["tier"].map(_TIER_MULTIPLIER)
    return grp[["conf", "avg_barthag", "tier", "translation"]]


def add_value_projection(players: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    """Attach a projected high-major value to every player.

    ``proj_value`` = PORPAG * translation multiplier — i.e. opponent-adjusted
    production, discounted for the jump in competition. ``value_score`` is that
    projection rescaled 0-100 across the candidate pool for readability.
    """
    df = players.copy()
    conf_str = conference_strength(teams)
    df = df.merge(conf_str[["conf", "tier", "translation"]], on="conf", how="left")
    df["translation"] = df["translation"].fillna(_TIER_MULTIPLIER[5])
    df["tier"] = df["tier"].fillna(5).astype(int)

    # Two-way value: PORPAG measures offensive points-over-replacement and
    # D-PORPAG (dporpag) the defensive equivalent, both on the same per-adjusted-
    # game scale, so they add up to a complete two-way value. Using only PORPAG
    # would systematically undervalue elite defenders who don't score much.
    df["dporpag"] = df["dporpag"].fillna(0)
    df["two_way_value"] = df["porpag"] + df["dporpag"]
    df["proj_value"] = df["two_way_value"] * df["translation"]
    # 0-100 scale via percentile rank within the pool (robust to outliers).
    df["value_score"] = (df["proj_value"].rank(pct=True) * 100).round(1)
    return df


# --------------------------------------------------------------------------- #
# 2. Roster need analysis
# --------------------------------------------------------------------------- #
_BUCKETS = ["Guard", "Wing", "Forward", "Big"]


def highmajor_minutes_share(players: pd.DataFrame) -> dict[str, float]:
    """Empirical minutes-share by position bucket across high-major teams.

    This is the "balanced rotation" the positional need is measured against —
    derived from the data (power-conference players, weighted by actual minutes
    played) rather than a hand-set assumption, so it self-calibrates each season.
    """
    hm = players[players["conf"].isin(POWER_CONFS)].copy()
    w = hm["min_pct"].fillna(0) * hm["games"].fillna(0)
    by_bucket = hm.assign(_w=w).groupby("pos_bucket")["_w"].sum()
    total = by_bucket.sum() or 1.0
    return {b: float(by_bucket.get(b, 0.0) / total) for b in _BUCKETS}

# Skills we grade players on, and the player-table column that measures each.
# ``higher_is_better`` is True for all of these.
SKILL_COLS = {
    "shooting": "jump_efg",      # eFG on jump shots (mid + 3, rim excluded) — pure shooting touch
    "playmaking": "ast_pct",
    "rebounding": "reb_pct",     # offensive + defensive rebound rate (both ends)
    "defense": "dporpag",        # holistic defensive value (was just block %)
    "ball_security": "to_pct",   # note: lower is better, handled below
    "scoring": "porpag",
}
_LOWER_IS_BETTER = {"ball_security"}


def _incoming_rows(players: pd.DataFrame, team: str, arrivals: set[str] | None) -> pd.DataFrame:
    """Player rows for simulated incoming signings (from other teams)."""
    if not arrivals:
        return players.iloc[0:0]
    arr = players[(players["player"].isin(arrivals)) & (players["team"] != team)]
    return arr.sort_values("min_pct", ascending=False).drop_duplicates("player")


def roster_need(
    players: pd.DataFrame,
    team: str,
    departing: set[str] | None = None,
    arrivals: set[str] | None = None,
) -> dict:
    """Diagnose what the projected roster lacks.

    ``departing`` is a set of player names assumed to leave (graduation, NBA,
    or transfer out); ``arrivals`` is a set of incoming-signing names from other
    teams folded into the roster. Needs are computed on returning − departing +
    arrivals, so the diagnosis reflects both.

    Returns a dict with per-bucket minutes deficits and per-skill gaps
    (negative = below the national high-major median = a need).
    """
    roster = players[players["team"] == team].copy()
    if departing is None:
        departing = set(roster.loc[roster["class"] == "Sr", "player"])
    returning = roster[~roster["player"].isin(departing)].copy()
    incoming = _incoming_rows(players, team, arrivals)
    if not incoming.empty:
        returning = pd.concat([returning, incoming], ignore_index=True)

    # --- positional need: compare returning minutes share to the high-major
    #     average (derived from the data, not a fixed assumption) ---
    target_share = highmajor_minutes_share(players)
    returning["min_weight"] = returning["min_pct"].fillna(0) * returning["games"].fillna(0)
    total_min = returning["min_weight"].sum() or 1.0
    pos_need = {}
    for bucket, target in target_share.items():
        have = returning.loc[returning["pos_bucket"] == bucket, "min_weight"].sum() / total_min
        pos_need[bucket] = round(target - have, 3)  # positive = need more here

    # --- skill need: compare returning roster to high-major baseline ---
    # Baseline = median among rotation players (>=40% minutes) on power-conf teams.
    # The gap is standardised to that population's std (z-score units) so it is
    # COMPARABLE across skills measured on very different scales — 3P% lives on
    # 0-1 while AST%/DRB%/TO% are 0-100 and PORPAG ~0-6, so raw gaps would make
    # shooting look permanently ~0 and distort the fit weighting.
    rotation = players[(players["min_pct"] >= 40) & (players["conf"].isin(POWER_CONFS))]
    skill_gap = {}
    for skill, col in SKILL_COLS.items():
        baseline = rotation[col].median()
        std = rotation[col].std(ddof=0)
        # weight returning players' skill by minutes
        w = returning["min_weight"]
        vals = returning[col]
        ok = vals.notna() & (w > 0)
        have = np.average(vals[ok], weights=w[ok]) if ok.any() else np.nan
        gap = (have - baseline) / std if std else 0.0   # standardised (σ units)
        if skill in _LOWER_IS_BETTER:
            gap = -gap  # invert so negative still means "worse than baseline"
        skill_gap[skill] = round(float(gap), 2) if pd.notna(gap) else 0.0

    return {
        "returning": returning,
        "departing": sorted(departing),
        "arrivals": sorted(arrivals or []),
        "pos_need": pos_need,
        "skill_gap": skill_gap,
    }


# --------------------------------------------------------------------------- #
# 3. Fit scoring
# --------------------------------------------------------------------------- #
def _zscore(series: pd.Series) -> pd.Series:
    std = series.std(ddof=0)
    if not std:
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


def score_fit(candidates: pd.DataFrame, need: dict) -> pd.DataFrame:
    """Score how well each candidate addresses Illinois's diagnosed needs.

    Combines a positional-need component (does the candidate play a bucket we
    are thin in?) and a skill-need component (does he supply skills we lack?).
    Returns the frame with a 0-100 ``fit_score`` column added.
    """
    df = candidates.copy()
    pos_need = need["pos_need"]
    skill_gap = need["skill_gap"]

    # Positional component: candidate gets credit proportional to how badly we
    # need his bucket (clipped at 0 — surplus buckets give no penalty here).
    max_pos = max(max(pos_need.values()), 0.01)
    df["pos_fit"] = df["pos_bucket"].map(
        lambda b: max(pos_need.get(b, 0), 0) / max_pos
    )

    # Skill component: reward candidates strong in the skills we most need.
    # Each skill is weighted by how thin we are in it — the weakest skill (most
    # negative gap) gets the most weight. Using a continuous weight (rather than
    # only outright deficits) means fit still differentiates candidates even when
    # the returning roster sits above the baseline everywhere.
    gaps = pd.Series(skill_gap, dtype=float)
    need_w = (gaps.max() - gaps) + 0.1      # weakest skill -> largest weight, all > 0
    need_w = need_w / need_w.sum()
    skill_fit = pd.Series(0.0, index=df.index)
    for skill, weight in need_w.items():
        col = SKILL_COLS[skill]
        z = _zscore(df[col].fillna(df[col].median()))
        if skill in _LOWER_IS_BETTER:
            z = -z
        skill_fit += weight * z
    # rescale skill_fit to 0-1 via percentile (within the candidate pool)
    df["skill_fit"] = skill_fit.rank(pct=True)

    # Blend skill and position into a 0-100 fit. We do NOT re-percentile the blend:
    # position is a bounded *lean* (max +25), not a hard gate. Re-percentiling would
    # segregate the board by the single most-needed position and bury elite players
    # of other positions.
    df["fit_score"] = ((0.75 * df["skill_fit"] + 0.25 * df["pos_fit"]) * 100).round(1)
    return df


# --------------------------------------------------------------------------- #
# 4. Full pipeline
# --------------------------------------------------------------------------- #
def find_targets(
    players: pd.DataFrame,
    teams: pd.DataFrame,
    *,
    own_team: str,
    departing: set[str] | None = None,
    arrivals: set[str] | None = None,
    min_games: int = 15,
    min_minutes: float = 40.0,
    include_classes: tuple[str, ...] = ("Fr", "So", "Jr"),
    value_weight: float = 0.6,
    positions: tuple[str, ...] | None = None,
    max_tier: int = 5,
) -> tuple[pd.DataFrame, dict]:
    """End-to-end: rank external transfer targets for ``own_team``.

    Returns ``(ranked_targets, need_diagnosis)``.

    ``value_weight`` blends projected value vs roster fit into ``target_score``
    (0.6 = value-led, the sensible default; a GM can slide it). ``include_classes``
    is the eligibility filter (seniors excluded by default). ``min_games`` /
    ``min_minutes`` guard against tiny-sample mirages.
    """
    pool = add_value_projection(players, teams)
    need = roster_need(players, own_team, departing, arrivals)

    # candidate universe: everyone NOT on our team (nor already signed), with
    # eligibility + sample guards.
    cand = pool[
        (pool["team"] != own_team)
        & (pool["games"] >= min_games)
        & (pool["min_pct"] >= min_minutes)
        & (pool["class"].isin(include_classes))
        & (pool["tier"] <= max_tier)
    ].copy()
    if arrivals:
        cand = cand[~cand["player"].isin(arrivals)]

    # Score over the FULL candidate pool (all positions) so value/fit/target are
    # comparable; the position filter is applied afterwards, as a display filter,
    # so a candidate's scores don't change when you narrow by position.
    cand = score_fit(cand, need)
    cand["target_score"] = (
        value_weight * cand["value_score"] + (1 - value_weight) * cand["fit_score"]
    ).round(1)
    cand = cand.sort_values("target_score", ascending=False)
    if positions:
        cand = cand[cand["pos_bucket"].isin(positions)]
    cand = cand.reset_index(drop=True)
    cand.insert(0, "board_rank", cand.index + 1)
    return cand, need
