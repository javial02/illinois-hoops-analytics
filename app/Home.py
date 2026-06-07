"""Illinois Hoops Analytics Hub — landing page.

Run with:  uv run streamlit run app/Home.py
"""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from illinois_hoops import scouting
from illinois_hoops.appkit import (block_i_png_uri, load_games, load_players,
                                   load_teams, page_setup, plot_bg,
                                   render_team_profile)
from illinois_hoops.config import BLUE, DEFAULT_SEASON, ORANGE, TEAM

page_setup(
    "Illinois Hoops Analytics Hub",
    "A public-data front-office toolkit — transfer-portal targeting, opponent scouting & roster construction.",
    nav="Home", filters_label="", sidebar_state="collapsed",
)

year = DEFAULT_SEASON
with st.sidebar:
    st.caption("Data: BartTorvik (opponent-adjusted, public) · 2025-26 season. "
               "The home page has no filters — use the Transfer Portal and Opponent "
               "Scouting pages for the interactive tools.")

teams = load_teams(year)

st.subheader("What this tool does")
c1, c2 = st.columns(2)
c1.markdown("#### Transfer Portal\n"
            "Profiles our roster and holes, ranks targets by **projected high-major "
            "value** **and fit** to our needs, and **simulates** how a signing would "
            "change the picture.")
c2.markdown("#### Opponent Scouting\n"
            "Auto-generates a four-factor scouting profile, key players, and "
            "**keys to the game** for any opponent.")

st.divider()

# --- Illinois profile (same format as Opponent Scouting; you can't scout
#     your own team there) ------------------------------------------------- #
games = load_games(year)
players = load_players(year)
ill_prof = scouting.team_profile(games, TEAM, compare="power")
ill_kp = scouting.key_players(players, TEAM)

st.subheader("Our team this season")
render_team_profile(ill_prof, ill_kp, heading="")   # donut + KPIs + four-factor + key players

st.divider()

# --- National efficiency landscape ----------------------------------------- #
st.subheader("National landscape — adjusted efficiency")
plot = teams.copy()
plot["highlight"] = plot["team"].apply(lambda t: TEAM if t == TEAM else "Other D-I")
fig = px.scatter(
    plot, x="adj_de", y="adj_oe", hover_name="team",
    color="highlight",
    color_discrete_map={TEAM: ORANGE, "Other D-I": "#c9c9c9"},
    labels={"adj_de": "Adjusted Defense (lower = better →)",
            "adj_oe": "Adjusted Offense (higher = better)"},
    height=560,
)
fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>"
                  "Adj. Offense  %{y:.1f}<br>Adj. Defense  %{x:.1f}<extra></extra>")
fig.update_xaxes(autorange="reversed")
fig.add_hline(y=plot["adj_oe"].median(), line_dash="dot", line_color="gray")
fig.add_vline(x=plot["adj_de"].median(), line_dash="dot", line_color="gray")
# hide Illinois's plain dot and drop the Block-I logo on its spot instead
fig.update_traces(marker=dict(size=0.1, opacity=0), showlegend=False,
                  selector=dict(name=TEAM))
ill_t = teams[teams["team"] == TEAM]
if not ill_t.empty:
    fig.add_layout_image(dict(
        source=block_i_png_uri(), xref="x", yref="y",
        x=float(ill_t.iloc[0]["adj_de"]), y=float(ill_t.iloc[0]["adj_oe"]),
        sizex=2.6, sizey=3.1, xanchor="center", yanchor="middle", layer="above",
    ))
fig.update_layout(plot_bgcolor=plot_bg(), paper_bgcolor=plot_bg(), font_color=BLUE,
                  legend_title_text="",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02,
                              xanchor="left", x=0))
st.plotly_chart(fig, theme=None, width="stretch")
st.caption("Top-right = elite on both ends. Each dot is a Division-I team; "
           f"{TEAM} highlighted in orange.")

st.divider()
st.caption("Built for the Illinois Men's Basketball Analytics Internship · "
           "Data sourced from barttorvik.com · Educational project.")
