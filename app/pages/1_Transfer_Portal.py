"""Transfer Portal — roster context, a ranked target board, and a fit simulator."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from illinois_hoops import portal, roster
from illinois_hoops.appkit import (load_players, load_teams, page_setup,
                                   plot_bg, section_header, sortable_table)
from illinois_hoops.config import BLUE, DEFAULT_SEASON, ORANGE, TEAM

page_setup("Transfer Portal",
           "Our roster and needs, a ranked board of targets, and a fit simulator. "
           "Every score is explainable.",
           nav="Transfer Portal")

# --------------------------------------------------------------------------- #
# Controls
# --------------------------------------------------------------------------- #
with st.sidebar:
    year = DEFAULT_SEASON
    players = load_players(year)
    teams = load_teams(year)

    own_roster = sorted(players[players["team"] == TEAM]["player"])
    senior_default = sorted(
        players[(players["team"] == TEAM) & (players["class"] == "Sr")]["player"]
    )
    st.subheader("Our departures")
    departing = set(st.multiselect(
        "Players leaving (graduation / NBA / transfer out)",
        own_roster, default=senior_default,
        help="Drives which positions and skills we need to replace.",
    ))
    # reserved slot for "Our arrivals" (filled below, once the board is known)
    arrivals_box = st.container()

    st.subheader("Candidate filters")
    classes = st.multiselect("Eligibility (class)", ["Fr", "So", "Jr", "Sr"],
                             default=["Fr", "So", "Jr"])
    gems_only = st.toggle("Hidden gems only (exclude power conferences)", value=False)
    positions = st.multiselect("Positions", ["Guard", "Wing", "Forward", "Big"])
    min_games = st.slider("Min games", 5, 35, 15)
    min_minutes = st.slider("Min minutes %", 10, 90, 40)
    value_weight = st.slider("Value vs Fit balance", 0.0, 1.0, 0.6, 0.05,
                             help="1.0 = pure projected value · 0.0 = pure roster fit")
    n = st.slider("Show top N (board size)", 10, 100, 25)
    compare = st.selectbox(
        "Compare skills vs", list(roster.SKILL_COMPARE_MODES.keys()), index=0,
        format_func=lambda k: roster.SKILL_COMPARE_MODES[k],
        help="Player pool the roster skill percentiles are measured against.",
    )

# Arrivals persist across reruns in session_state; read the prior pick to build
# the board, then offer EXACTLY the board players as arrival options — so every
# player on the board is one you can actually sign and simulate (and vice versa).
_prev = st.session_state.get("arrivals_sel", [])
arrivals = {lbl.rsplit(" (", 1)[0] for lbl in _prev}

targets, need = portal.find_targets(
    players, teams, own_team=TEAM, departing=departing, arrivals=arrivals,
    min_games=min_games, min_minutes=min_minutes,
    include_classes=tuple(classes) or ("Fr", "So", "Jr"),
    value_weight=value_weight,
    positions=tuple(positions) or None,
    max_tier=5,
)
if gems_only:
    targets = targets[targets["tier"] >= 2].reset_index(drop=True)
    targets["board_rank"] = targets.index + 1
board = targets.head(n)

# Our arrivals — options are the board players (+ already-signed, so the pick
# never vanishes when a signed player drops off the board). Rendered into the
# slot reserved under "Our departures".
_arr_opts = list(dict.fromkeys(
    [f"{r.player} ({r.team})" for r in board.itertuples()] + _prev))
with arrivals_box:
    st.subheader("Our arrivals")
    st.multiselect(
        "Players we'd sign (from the board)", _arr_opts, key="arrivals_sel",
        help="Only board players can be signed — folded into the needs, board and radar.",
    )

# --------------------------------------------------------------------------- #
# Our roster
# --------------------------------------------------------------------------- #
with st.expander("Glossary — the metrics & skills used on this page",
                 icon=":material/info:"):
    st.markdown(
        "- **PORPAG / D-PORPAG** — opponent-adjusted **offensive / defensive value** "
        "(points produced over a replacement-level player, per game).\n"
        "- **Proj. value** — PORPAG + D-PORPAG **discounted by a competition-level "
        "multiplier** (production in a weaker league is worth less at high-major).\n"
        "- **Value / Fit / Target score** — 0–100 **percentiles** within the candidate "
        "pool. *Value* = how good · *Fit* = how well he fills our holes · *Target "
        "score* = the blend (set by the **Value vs Fit balance** slider).\n"
        "- **Skills** — shooting (long-shot eFG%: mid-range + 3s, rim excluded), "
        "playmaking (AST%), rebounding (REB% = off+def), defense (D-PORPAG), "
        "ball security (TO%, inverted), scoring (PORPAG)."
    )

section_header(f"{TEAM} roster", "players")
# Identity + one stat per radar skill: scoring (PORPAG/PPG), shooting (3P%),
# playmaking (AST%), rebounding (DRB%), defense (D-PORPAG), ball security (TO%).
_rcols = ["player", "status", "class", "position", "height", "min_pct", "ppg",
          "porpag", "jump_efg", "ast_pct", "reb_pct", "dporpag", "to_pct"]
rost = roster.get_roster(players, TEAM, departing)
disp = rost[_rcols].copy()
if arrivals:
    inc = players[(players["player"].isin(arrivals)) & (players["team"] != TEAM)]
    inc = inc.sort_values("min_pct", ascending=False).drop_duplicates("player").copy()
    inc["status"] = "Incoming"
    disp = pd.concat([disp, inc[_rcols]], ignore_index=True)
for col, fmt in {"min_pct": "{:.1f}", "ppg": "{:.1f}", "porpag": "{:.1f}",
                 "ast_pct": "{:.1f}", "reb_pct": "{:.1f}",
                 "dporpag": "{:.1f}", "to_pct": "{:.1f}"}.items():
    disp[col] = disp[col].map(lambda x, f=fmt: f.format(x) if pd.notna(x) else "")
# long-range shooting: dash when there aren't enough attempts to compute it
disp["jump_efg"] = disp["jump_efg"].map(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
disp.columns = ["Player", "Status", "Yr", "Position", "Ht", "Min%", "PPG",
                "PORPAG", "Long-shot %", "AST%", "REB%", "D-PORPAG", "TO%"]
sortable_table(disp)

# --------------------------------------------------------------------------- #
# Roster need diagnosis
# --------------------------------------------------------------------------- #
section_header("Roster need diagnosis", "diagnosis")
st.caption("What our **projected roster** (who returns − departures + arrivals) is "
           "short on, by position and by skill. These gaps are exactly what the "
           "board below scores candidates against.")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Positional need** — where we're thin")
    st.caption("Bar = a balanced high-major rotation's share of minutes at that "
               "position **minus** ours. **Above 0** = we play it *less* than a "
               "balanced rotation, so we're thin and need more there; **below 0** = "
               "we already have more than enough.")
    pos = need["pos_need"]
    posfig = px.bar(x=list(pos.keys()), y=list(pos.values()),
                    color=[v for v in pos.values()],
                    color_continuous_scale=["#cccccc", ORANGE],
                    labels={"x": "", "y": "Need (↑ = thinner)"})
    posfig.update_traces(hovertemplate="<b>%{x}</b><br>Need %{y:+.2f} "
                         "(+ = thinner)<extra></extra>")
    posfig.update_layout(coloraxis_showscale=False, height=300, plot_bgcolor=plot_bg(),
                         paper_bgcolor=plot_bg(), font_color=BLUE)
    st.plotly_chart(posfig, theme=None, width="stretch")
with c2:
    st.markdown("**Skill gap** — how we stack up per skill")
    st.caption("Bar = our roster's value on that skill **minus** the high-major "
               "rotation median, in standard deviations (σ). Right of 0 (navy) = "
               "above the high-major average; left of 0 (orange) = below.")
    sg = need["skill_gap"]
    colors = [BLUE if v >= 0 else ORANGE for v in sg.values()]
    labels = [s.replace("_", " ").title() for s in sg.keys()]
    skfig = px.bar(x=list(sg.values()), y=labels, orientation="h")
    skfig.update_traces(marker_color=colors,
                        hovertemplate="<b>%{y}</b><br>%{x:+.2f} σ vs high-major"
                                      "<extra></extra>")
    skfig.add_vline(x=0, line_color="gray")
    skfig.update_layout(height=300, plot_bgcolor=plot_bg(), paper_bgcolor=plot_bg(),
                        font_color=BLUE, xaxis_title="gap (σ vs high-major)",
                        yaxis_title="")
    st.plotly_chart(skfig, theme=None, width="stretch")

# --------------------------------------------------------------------------- #
# The board
# --------------------------------------------------------------------------- #
section_header("Target board", "target")
st.caption("Our ranked recruiting board: every eligible transfer candidate scored "
           "by **Target score** — a 0–100 blend of projected high-major value and "
           "fit to the needs above. The top **N** (sidebar slider) are shown; click "
           "any column header to sort.")
show = board[["board_rank", "player", "team", "conf", "class", "pos_bucket",
              "porpag", "dporpag", "proj_value", "value_score", "fit_score",
              "target_score"]].copy()
for col, fmt in {"porpag": "{:.1f}", "dporpag": "{:.1f}", "proj_value": "{:.1f}",
                 "value_score": "{:.0f}", "fit_score": "{:.0f}",
                 "target_score": "{:.1f}"}.items():
    show[col] = show[col].map(lambda x, f=fmt: f.format(x) if pd.notna(x) else "")
show["board_rank"] = show["board_rank"].astype(int)
show.columns = ["#", "Player", "Team", "Conf", "Yr", "Pos", "PORPAG", "D-PORPAG",
                "Proj. value", "Value", "Fit", "Target score"]
sortable_table(show, bar_col="Target score")

# value vs fit scatter — a quadrant zoomed to the shortlist shown.
st.subheader("Value vs Fit")
plot = board.copy()
sc = px.scatter(plot, x="fit_score", y="value_score", hover_name="player",
                size="target_score", color="pos_bucket", text="player",
                size_max=12, opacity=0.78,
                labels={"fit_score": "Fit to our needs →",
                        "value_score": "Projected value →"},
                height=560)
sc.update_traces(textposition="top center", textfont_size=10,
                 marker=dict(line=dict(width=0.5, color="white")),
                 hovertemplate="<b>%{hovertext}</b><br>"
                               "Fit %{x:.0f} · Value %{y:.0f}<extra></extra>")
sc.add_hline(y=plot["value_score"].median(), line_dash="dot", line_color="gray")
sc.add_vline(x=plot["fit_score"].median(), line_dash="dot", line_color="gray")
sc.update_layout(plot_bgcolor=plot_bg(), paper_bgcolor=plot_bg(), font_color=BLUE,
                 legend_title_text="Position",
                 legend=dict(orientation="h", yanchor="bottom", y=1.02,
                             xanchor="left", x=0))
st.plotly_chart(sc, theme=None, width="stretch")
st.caption("Axes are 0-100 percentiles within the candidate pool; the chart is "
           "zoomed to the shortlist shown. The dotted lines are the **medians of "
           "the names shown** (they sit high — e.g. ~99 / ~98 — because everyone on "
           "the board is already elite), splitting it into quadrants: top-right = "
           "best of the board on both value **and** fit. Hover any dot for its "
           "numbers; lower **Show top N** for a less crowded chart.")

# --------------------------------------------------------------------------- #
# Roster impact — returning vs the projected roster (with the sidebar arrivals)
# --------------------------------------------------------------------------- #
section_header("Roster impact", "transfer")
st.caption("How our roster's skill profile changes with the moves you set in the "
           "sidebar. Each axis is a percentile (0-100) vs the chosen player pool — "
           "**Current** = roster as-is, **Projected** = after departures + arrivals.")
# "Current" = the full roster as-is (no moves); "Projected" = after both the
# departures AND the arrivals — so losing players shows up as impact too.
current_prof = roster.roster_profile(players, TEAM, departing=set(), compare=compare)
projected_prof = roster.roster_profile(players, TEAM, departing=departing,
                                       compare=compare, arrivals=arrivals)
before, after = current_prof["skill_profile"], projected_prof["skill_profile"]
SKILLS = list(before.keys())
has_change = bool(departing) or bool(arrivals)

left, right = st.columns([1, 1])
with left:
    fig = go.Figure()
    cats = [s.replace("_", " ").title() for s in SKILLS + [SKILLS[0]]]
    fig.add_trace(go.Scatterpolar(
        r=[before[s] for s in SKILLS] + [before[SKILLS[0]]],
        theta=cats, fill="toself", name="Current", line_color=BLUE))
    if has_change:
        fig.add_trace(go.Scatterpolar(
            r=[after[s] for s in SKILLS] + [after[SKILLS[0]]],
            theta=cats, fill="toself", name="Projected", line_color=ORANGE))
    fig.update_layout(
        polar=dict(
            bgcolor="#ffffff", gridshape="linear",
            radialaxis=dict(range=[0, 100], gridcolor="#d6d6d6", linecolor="#d6d6d6"),
            angularaxis=dict(gridcolor="#d6d6d6", linecolor="#d6d6d6"),
        ),
        paper_bgcolor="#ffffff", font_color=BLUE, height=460, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.04,
                    xanchor="center", x=0.5))
    fig.update_traces(hovertemplate="<b>%{theta}</b><br>%{r:.0f}th percentile"
                                    "<extra>%{fullData.name}</extra>")
    st.plotly_chart(fig, theme=None, width="stretch")
    st.caption(f"Percentiles vs **{projected_prof['compare_label']}** "
               f"({projected_prof['n_ref']} players). Bigger shape = better.")

with right:
    if has_change:
        st.markdown("**Impact of your moves** (departures + arrivals)")
        mcols = st.columns(2)
        for i, s in enumerate(SKILLS):
            delta = after[s] - before[s]
            mcols[i // 3].metric(s.replace("_", " ").title(), f"{after[s]:.0f}",
                                 f"{delta:+.0f}",
                                 delta_color="off" if delta == 0 else "normal")
    else:
        st.info("Pick **departures** and/or **arrivals** in the sidebar to project "
                "the roster and see the impact here.")
