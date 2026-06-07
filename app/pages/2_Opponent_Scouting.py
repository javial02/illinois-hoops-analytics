"""Opponent Scouting — auto-generated four-factor report for any team."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from illinois_hoops import scouting
from illinois_hoops.appkit import (load_games, load_players, page_setup,
                                   render_team_profile, section_header,
                                   icon_label, white_table)
from illinois_hoops.config import DEFAULT_SEASON, ORANGE, TEAM

page_setup("Opponent Scouting Report",
           "Four-factor identity, performance context, and auto-generated keys to the game.",
           nav="Opponent Scouting")

with st.sidebar:
    year = DEFAULT_SEASON
    games = load_games(year)
    all_teams = sorted(games["team"].unique())
    default_idx = all_teams.index("Purdue") if "Purdue" in all_teams else 0
    opponent = st.selectbox("Scout this team", all_teams, index=default_idx)

    compare_keys = list(scouting.COMPARE_MODES.keys())
    compare = st.selectbox(
        "Compare percentiles vs", compare_keys, index=0,
        format_func=lambda k: scouting.COMPARE_MODES[k],
        help="Which population the four-factor percentiles are measured against.",
    )

prof = scouting.team_profile(games, opponent, compare=compare)
rep = scouting.scouting_report(prof)
players = load_players(year)
kp = scouting.key_players(players, opponent)

# headline metrics + four-factor charts + key players (shared with Home)
render_team_profile(prof, kp)

# --- auto scouting notes --------------------------------------------------- #
section_header("Scouting notes", "notes")
c1, c2, c3 = st.columns(3)
with c1:
    icon_label("Strengths", "check", "#5BD08A")
    for s in rep["strengths"]:
        st.markdown(f"- {s}")
with c2:
    icon_label("Weaknesses", "alert", ORANGE)
    for w in rep["weaknesses"]:
        st.markdown(f"- {w}")
with c3:
    icon_label(f"Keys to the game (if {TEAM} plays them)", "target", "#7FA1C9")
    for k in rep["keys_to_game"]:
        st.markdown(f"- {k}")

# --- game log -------------------------------------------------------------- #
with st.expander("Full game log"):
    log = prof["log"][["date", "opponent", "venue", "result", "off_rtg",
                       "def_rtg", "adj_margin"]].copy()
    for col, fmt in {"off_rtg": "{:.1f}", "def_rtg": "{:.1f}", "adj_margin": "{:+.1f}"}.items():
        log[col] = log[col].map(lambda x, f=fmt: f.format(x) if pd.notna(x) else "")
    log.columns = ["Date", "Opponent", "Venue", "Result", "Off Rtg", "Def Rtg", "Adj Margin"]
    st.markdown(white_table(log), unsafe_allow_html=True)

st.divider()
st.caption("Four factors (Dean Oliver): shooting (eFG%), turnovers (TO%), "
           "rebounding (ORB%), free-throw rate. Percentiles vs all of Division I.")
