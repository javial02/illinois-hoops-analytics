"""Shared Streamlit helpers: cached data loaders and Illinois branding.

Kept in the package (not the app folder) so every page imports it the same way
regardless of Streamlit's working directory. Owns the Block-I logo, the (single,
light) visual theme, the top navigation bar and the matching Plotly template.
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
import streamlit.components.v1 as components

from . import data
from .config import BLUE, LIGHT, ORANGE

_ASSETS = Path(__file__).resolve().parent / "assets"


@st.cache_data
def _bg_data_uri() -> str:
    """Base64 data URI of the arena background image (empty if missing)."""
    img = _ASSETS / "arena.jpg"
    if not img.exists():
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(img.read_bytes()).decode()

SEASONS = [2026, 2025, 2024]

# Top navigation: (label, page URL, icon). RELATIVE urls so links work whether
# the app is served at the domain root (local) or under a base path (Streamlit
# Cloud) — absolute "/Page" links break on a non-root deployment.
NAV = [
    ("Home", ".", "home"),
    ("Transfer Portal", "Transfer_Portal", "transfer"),
    ("Opponent Scouting", "Opponent_Scouting", "search"),
]

PLOT_BG = "#FFFFFF"


@st.cache_data(show_spinner="Loading player data from BartTorvik…")
def load_players(year: int) -> pd.DataFrame:
    return data.fetch_players(year)


@st.cache_data(show_spinner="Loading team data from BartTorvik…")
def load_teams(year: int) -> pd.DataFrame:
    return data.fetch_teams(year)


@st.cache_data(show_spinner="Loading game data from BartTorvik…")
def load_games(year: int) -> pd.DataFrame:
    return data.fetch_games(year)


def plot_bg() -> str:
    return PLOT_BG


# --------------------------------------------------------------------------- #
# Block-I logo (hand-built SVG — scalable, no external image dependency)
# --------------------------------------------------------------------------- #
def block_i(height: int = 34, fill: str = ORANGE, outline: str = BLUE,
            outline_w: float = 6) -> str:
    """Return an inline SVG of an Illinois-style Block I at the given height."""
    pts = "8,4 92,4 92,30 63,30 63,94 92,94 92,116 8,116 8,94 37,94 37,30 8,30"
    w = round(height * 100 / 120)
    return (
        f'<svg width="{w}" height="{height}" viewBox="0 0 100 120" '
        f'style="vertical-align:middle">'
        f'<polygon points="{pts}" fill="{fill}" stroke="{outline}" '
        f'stroke-width="{outline_w}" stroke-linejoin="round"/></svg>'
    )


_BLOCK_I_PTS = [(8, 4), (92, 4), (92, 30), (63, 30), (63, 94), (92, 94),
                (92, 116), (8, 116), (8, 94), (37, 94), (37, 30), (8, 30)]


@st.cache_data
def block_i_png_uri(scale: int = 4) -> str:
    """Base64 PNG data URI of the Block-I (transparent bg) — for use as a Plotly
    layout image / point marker. PNG (not SVG) so Plotly renders it reliably."""
    from PIL import Image, ImageDraw  # local import: only needed for this feature

    w, h = 100 * scale, 120 * scale
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pts = [(x * scale, y * scale) for x, y in _BLOCK_I_PTS]
    draw.polygon(pts, fill=(255, 95, 5, 255), outline=(19, 41, 75, 255),
                 width=max(2, scale * 2))
    buf = BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# --------------------------------------------------------------------------- #
# Line icons (simple, single-stroke, Illinois-coloured — replace emoji)
# --------------------------------------------------------------------------- #
_ICON_PATHS = {
    # clipboard with lines — roster need diagnosis
    "diagnosis": ('<rect x="8" y="2" width="8" height="4" rx="1"/>'
                  '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6'
                  'a2 2 0 0 1 2-2h2"/><path d="M9 12h6"/><path d="M9 16h6"/>'),
    # concentric target — shortlist / keys to the game
    "target": ('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/>'
               '<circle cx="12" cy="12" r="1.7" fill="__C__" stroke="none"/>'),
    # document with lines — scouting notes
    "notes": ('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
              '<path d="M14 2v6h6"/><path d="M9 13h6"/><path d="M9 17h6"/>'),
    # check in a circle — strengths
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8.3 12.4l2.6 2.6 4.8-5.4"/>',
    # warning triangle — weaknesses
    "alert": ('<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3'
              'L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 16.6h.01"/>'),
    # people — key players section
    "players": ('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
                '<circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/>'
                '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'),
    # trending up — offence
    "offense": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    # shield — defence
    "defense": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    # house — Home nav
    "home": ('<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>'
             '<path d="M9.5 21v-6h5v6"/>'),
    # in/out arrows — Transfer Portal nav
    "transfer": ('<path d="M7 4 3 8l4 4"/><path d="M3 8h13"/>'
                 '<path d="M17 20l4-4-4-4"/><path d="M21 16H8"/>'),
    # magnifier — Opponent Scouting nav
    "search": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.2-4.2"/>',
}

_NAME_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def _initials(name: str) -> str:
    parts = [p for p in name.split() if p.strip(".").lower() not in _NAME_SUFFIXES]
    parts = parts or name.split()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def avatar(name: str, color: str = BLUE, size: int = 52) -> str:
    """A round initials avatar (no external image dependency)."""
    return (f'<div class="pc-avatar" style="width:{size}px;height:{size}px;'
            f'background:{color};font-size:{round(size * 0.36)}px">'
            f'{_initials(name)}</div>')


def white_table(df: pd.DataFrame, bar_col: str | None = None,
                bar_max: float = 100.0) -> str:
    """Render a DataFrame as a clean white-card HTML table (values pre-formatted
    as strings). ``bar_col`` renders that column as an orange progress bar."""
    head = "".join(f"<th>{c}</th>" for c in df.columns)
    body = []
    for _, r in df.iterrows():
        cells = []
        for c in df.columns:
            v = r[c]
            if c == bar_col:
                try:
                    pct = max(0.0, min(100.0, float(v) / bar_max * 100))
                except (TypeError, ValueError):
                    pct = 0.0
                cell = (f'<div class="wt-bar"><div class="wt-bar-fill" '
                        f'style="width:{pct:.0f}%"></div>'
                        f'<span class="wt-bar-txt">{v}</span></div>')
            else:
                cell = "" if (v is None or (isinstance(v, float) and pd.isna(v))) else v
            cells.append(f"<td>{cell}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return (f'<div class="wt-card"><table class="wt"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def sortable_table(df: pd.DataFrame, *, bar_col: str | None = None,
                   bar_max: float = 100.0, row_height: int | None = None) -> None:
    """White-card table whose columns sort on click (with a ▲/▼ arrow).

    Rendered inside a self-contained iframe (so the sort JS actually runs) while
    keeping the same white styling as :func:`white_table`. ``bar_col`` renders
    that column as an orange progress bar; values are pre-formatted strings.
    """
    cols = list(df.columns)
    head = "".join(
        f'<th onclick="sortTable({i})">{c}<span class="arr"></span></th>'
        for i, c in enumerate(cols)
    )
    body = []
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if c == bar_col:
                try:
                    pct = max(0.0, min(100.0, float(v) / bar_max * 100))
                except (TypeError, ValueError):
                    pct = 0.0
                cell = (f'<div class="wt-bar"><div class="wt-bar-fill" '
                        f'style="width:{pct:.0f}%"></div>'
                        f'<span class="wt-bar-txt">{v}</span></div>')
            else:
                cell = "" if (v is None or (isinstance(v, float) and pd.isna(v))) else v
            cells.append(f"<td>{cell}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")

    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
      *{{box-sizing:border-box;}}
      body{{margin:0;background:transparent;
        font-family:"Source Sans Pro",system-ui,-apple-system,sans-serif;}}
      .wt-card{{background:#fff;border:1px solid #e2e2e2;border-radius:8px;
        padding:.2rem .4rem;overflow:hidden;}}
      table.wt{{width:100%;border-collapse:collapse;font-size:.76rem;color:{BLUE};}}
      table.wt th{{text-align:left;color:#6a7385;font-weight:700;font-size:.64rem;
        text-transform:uppercase;letter-spacing:.02em;padding:.32rem .5rem;
        border-bottom:2px solid #eee;white-space:nowrap;cursor:pointer;user-select:none;
        transition:color .15s;}}
      table.wt th:hover{{color:{ORANGE};}}
      table.wt td{{padding:.28rem .5rem;border-bottom:1px solid #f2f2f2;
        white-space:nowrap;color:{BLUE};}}
      table.wt tbody tr:last-child td{{border-bottom:none;}}
      table.wt tbody tr:hover td{{background:#fff7f2;}}
      .arr{{color:{ORANGE};font-size:.7rem;margin-left:.2rem;
        display:inline-block;transition:transform .15s;}}
      .wt-bar{{position:relative;background:#eef0f3;border-radius:6px;
        height:18px;min-width:90px;}}
      .wt-bar-fill{{position:absolute;left:0;top:0;bottom:0;background:{ORANGE};
        border-radius:6px;}}
      .wt-bar-txt{{position:relative;padding-left:.45rem;font-weight:700;
        font-size:.75rem;line-height:18px;color:{BLUE};}}
    </style></head><body>
      <div class="wt-card"><table class="wt" id="wt" data-col="-1" data-dir="">
        <thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>
      <script>
      function sortTable(n){{
        var t=document.getElementById('wt'),tb=t.tBodies[0];
        var rows=Array.prototype.slice.call(tb.rows);
        var dir=(t.getAttribute('data-col')==n&&t.getAttribute('data-dir')=='asc')?'desc':'asc';
        rows.sort(function(a,b){{
          var x=a.cells[n].innerText.trim(),y=b.cells[n].innerText.trim();
          var xn=parseFloat(x.replace(/[^0-9.-]/g,'')),yn=parseFloat(y.replace(/[^0-9.-]/g,''));
          var num=!isNaN(xn)&&!isNaN(yn)&&/^[-0-9.]/.test(x)&&/^[-0-9.]/.test(y);
          var c=num?(xn-yn):x.localeCompare(y);
          return dir=='asc'?c:-c;
        }});
        rows.forEach(function(r){{tb.appendChild(r);}});
        t.setAttribute('data-col',n);t.setAttribute('data-dir',dir);
        var ths=t.tHead.rows[0].cells;
        for(var i=0;i<ths.length;i++){{
          ths[i].querySelector('.arr').textContent=(i==n)?(dir=='asc'?'\\u25B2':'\\u25BC'):'';
        }}
      }}
      </script>
    </body></html>"""
    # tight fit: header(23) + rows*row_height + card padding/border(~8) + 2px buffer.
    rh = row_height if row_height else (28 if bar_col else 25)
    components.html(html, height=33 + len(df) * rh, scrolling=False)


def kpi_card(label: str, value: str, sub: str = "", badge: str = "",
             note: str = "") -> str:
    """A dark-navy KPI card.

    ``badge`` shows a small green pill to the right of the value; ``note`` shows
    small muted text to the right of the value (inline); ``sub`` shows a small
    muted line below it.
    """
    badge_html = f'<span class="kpi-badge">{badge}</span>' if badge else ""
    note_html = f'<span class="kpi-note">{note}</span>' if note else ""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return (f'<div class="kpi"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-row"><span class="kpi-value">{value}</span>'
            f'{badge_html}{note_html}</div>{sub_html}</div>')


def icon(name: str, color: str = BLUE, size: int = 20, margin: str = ".5rem") -> str:
    """Return an inline line-icon SVG. ``color`` may be ``currentColor`` to
    inherit the surrounding text colour; ``margin`` sets the right margin."""
    paths = _ICON_PATHS[name].replace("__C__", color)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" style="vertical-align:-3px;margin-right:{margin}">'
        f'{paths}</svg>'
    )


def section_header(title: str, name: str, color: str = ORANGE) -> None:
    """A section heading (h3) prefixed with a simple Illinois-coloured icon."""
    st.markdown(f'<h3 class="hub-section">{icon(name, color, 22)}{title}</h3>',
                unsafe_allow_html=True)


def icon_label(text: str, name: str, color: str = ORANGE) -> None:
    """A bold inline label prefixed with a small icon (for sub-blocks)."""
    st.markdown(f'<p class="hub-iconlabel">{icon(name, color, 18)}'
                f'<strong>{text}</strong></p>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Team scouting profile — shared by Opponent Scouting and Home (Illinois)
# --------------------------------------------------------------------------- #
def _factor_fig(block: dict, title: str, color: str):
    labels = list(block.keys())
    pcts = [block[k]["pct"] for k in labels]
    vals = [block[k]["value"] for k in labels]
    fig = go.Figure(go.Bar(
        x=pcts, y=labels, orientation="h", marker_color=color,
        text=[f"{v} ({p:.0f}th)" for v, p in zip(vals, pcts)],
        textposition="outside", customdata=vals,
        hovertemplate="<b>%{y}</b><br>%{customdata} · %{x:.0f}th percentile"
                      "<extra></extra>",
    ))
    fig.update_layout(title=title, xaxis_range=[0, 122], height=300, autosize=False,
                      margin=dict(l=75, r=40, t=45, b=70), bargap=0.45,
                      plot_bgcolor=PLOT_BG, paper_bgcolor=PLOT_BG,
                      font_color=BLUE, xaxis_title="percentile")
    fig.update_xaxes(fixedrange=True)   # no zoom/pan on this display chart
    fig.update_yaxes(fixedrange=True)
    fig.add_vline(x=50, line_dash="dot", line_color="gray")
    return fig


def _fmt(value, decimals=1):
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def _player_card(pl: dict, side: str) -> None:
    color = ORANGE if side == "offense" else BLUE
    if side == "offense":
        stats = [("PPG", _fmt(pl.get("ppg"))), ("PORPAG", _fmt(pl.get("porpag"))),
                 ("USG%", _fmt(pl.get("usage"), 0)), ("TS%", _fmt(pl.get("ts"), 0))]
    else:
        stats = [("D-PORPAG", _fmt(pl.get("dporpag"))), ("DRB%", _fmt(pl.get("drb_pct"), 0)),
                 ("STL%", _fmt(pl.get("stl_pct"))), ("BLK%", _fmt(pl.get("blk_pct")))]
    chips = "".join(
        f'<div class="pc-stat"><span class="pc-v">{v}</span>'
        f'<span class="pc-k">{k}</span></div>' for k, v in stats
    )
    st.markdown(
        f'<div class="pcard"><div class="pc-head">{avatar(pl["player"], color)}'
        f'<div><div class="pc-name">{pl["player"]}</div>'
        f'<div class="pc-sub">{pl.get("class","")} · {pl.get("position","")}</div>'
        f'</div></div><div class="pc-stats">{chips}</div></div>',
        unsafe_allow_html=True,
    )


_NO_ZOOM = {"displayModeBar": False, "scrollZoom": False}

KPI_HELP = ("**Net Rating** = adjusted points margin per 100 possessions "
            "(offense − defense; the + sign shows it can be negative) · "
            "**Offense / Defense** = adjusted points scored / allowed per 100 "
            "(lower defense is better) · **Tempo** = possessions per 40 min · "
            "**vs Power confs** = record vs ACC/B10/B12/SEC/BE · **Recent form** "
            "= last 10 games.")


def record_donut(record: str):
    """A transparent win/loss donut (orange wins, blue losses, record in the hole)."""
    wins, losses = (int(x) for x in record.split("-"))
    pct = wins / (wins + losses) * 100 if (wins + losses) else 0
    fig = go.Figure(go.Pie(
        values=[wins, losses], labels=["Wins", "Losses"], hole=0.62, sort=False,
        direction="clockwise",
        marker=dict(colors=[ORANGE, "#5f7da8"], line=dict(color="rgba(0,0,0,0)", width=2)),
        textinfo="label+value", textposition="inside",
        insidetextorientation="horizontal", textfont=dict(color="white", size=12),
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>"))
    fig.update_layout(
        height=250, margin=dict(t=8, b=8, l=8, r=8), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(text=f"<b>{wins}-{losses}</b><br>{pct:.0f}% wins",
                          x=0.5, y=0.5, showarrow=False,
                          font=dict(size=16, color="#E8EEF7"))])
    return fig


def render_kpis(prof: dict, ncols: int = 6) -> None:
    """The six headline KPI cards laid out in ``ncols`` columns (6 = one row,
    3 = a 2x3 grid). Rendered row by row so rows align and are spaced apart."""
    rf_val, _, rf_sub = prof["recent_form"].partition(" (")
    items = [
        ("Net Rating", f"{prof['net_rtg']:+.1f}", {}),
        ("Offense", f"{prof['off_rtg']:.1f}", {}),
        ("Defense", f"{prof['def_rtg']:.1f}", {}),
        ("Tempo", f"{prof['tempo']:.1f}", {"badge": f"↑ {prof['tempo_pct']:.0f}th pct"}),
        ("vs Power confs", prof["vs_power_record"], {}),
        ("Recent form", rf_val, {"note": rf_sub.rstrip(")")}),
    ]
    for start in range(0, len(items), ncols):
        cols = st.columns(ncols, gap="medium")
        for col, (label, val, kw) in zip(cols, items[start:start + ncols]):
            col.markdown(kpi_card(label, val, **kw), unsafe_allow_html=True)


def render_team_profile(prof: dict, key_players: dict, heading: str | None = None,
                        show_kpis: bool = True) -> None:
    """Render the KPI cards, four-factor charts and key-player cards for a team.

    Shared by Opponent Scouting (any team) and the Home page (Illinois). Pass
    ``heading=""`` to suppress the "{team} — {record}" title, and
    ``show_kpis=False`` when the page already renders the KPIs itself.
    """
    head = prof["team"] if heading is None else heading
    if head:
        st.subheader(head)
    if show_kpis:
        dcol, kcol = st.columns([1, 1.7], vertical_alignment="center")
        with dcol:
            st.plotly_chart(record_donut(prof["record"]), theme=None,
                            width="stretch", config={"displayModeBar": False})
        with kcol:
            render_kpis(prof, 3)
        st.caption(KPI_HELP)

    st.subheader(f"Four-factor profile (percentile vs {prof['compare_label']})")
    st.caption("The **four factors** (Dean Oliver) are the four things that win a "
               "possession — **shooting** (eFG%), **turnovers** (TO%), **rebounding** "
               "(ORB%) and **free throws** (FTRate). Each is shown as a percentile vs "
               f"**{prof['compare_label']}** ({prof['n_ref']} teams), graded on offense "
               "and defense (higher = better; defensive factors oriented so higher = "
               "harder to score on). The dotted line is the 50th percentile.")
    col_o, col_d = st.columns(2)
    col_o.plotly_chart(_factor_fig(prof["offense"], "Offense", ORANGE),
                       theme=None, width="stretch", config=_NO_ZOOM)
    col_d.plotly_chart(_factor_fig(prof["defense"], "Defense", BLUE),
                       theme=None, width="stretch", config=_NO_ZOOM)

    section_header("Key players", "players")
    col_off, col_def = st.columns(2)
    with col_off:
        icon_label("Top offensive players", "offense", ORANGE)
        for pl in key_players["offense"]:
            _player_card(pl, "offense")
    with col_def:
        icon_label("Top defensive players", "defense", BLUE)
        for pl in key_players["defense"]:
            _player_card(pl, "defense")
    st.caption("Offence ranked by PORPAG, defence by D-PORPAG — both opponent-"
               "adjusted. Rotation players only (≥40% minutes).")
    st.caption("**Card stats** — **PPG** points per game · **PORPAG / D-PORPAG** "
               "offensive / defensive value · **USG%** share of possessions the "
               "player uses while on court (~20% = average) · **TS%** true-shooting "
               "efficiency incl. free throws · **DRB%** defensive rebounds grabbed of "
               "those available · **STL% / BLK%** opponent possessions ending in his "
               "steal / 2-pt attempts he blocks. The “%” stats are rates of "
               "opportunities while on court, not per game.")


# --------------------------------------------------------------------------- #
# Plotly template (single light theme)
# --------------------------------------------------------------------------- #
def _install_plot_template() -> None:
    pio.templates["illini"] = go.layout.Template(layout=dict(
        paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG,
        font=dict(color=BLUE, family="sans-serif"),
        xaxis=dict(gridcolor="#ececec", zerolinecolor="#ececec"),
        yaxis=dict(gridcolor="#ececec", zerolinecolor="#ececec"),
        colorway=[ORANGE, BLUE, "#7FA1C9", "#F2A900", "#9aa6b2", "#5b8c5a"],
    ))
    pio.templates.default = "plotly+illini"


# --------------------------------------------------------------------------- #
# Page chrome
# --------------------------------------------------------------------------- #
def _inject_css() -> None:
    bg = _bg_data_uri()
    # Photo on .stApp WITHOUT `background-attachment: fixed` (that repaints every
    # scroll frame and causes the stepped-corner artifact). .stApp is the static
    # outer container — its child scrolls — so the photo still looks fixed.
    app_bg = (
        f'background-color: #0C1730; background-image: '
        f'linear-gradient(rgba(8,16,33,.86), rgba(8,16,33,.93)), url("{bg}"); '
        f'background-size: cover; background-position: center; '
        f'background-repeat: no-repeat;'
        if bg else "background-color: #0C1730;"
    )
    st.markdown(
        f"""
        <style>
            /* hide Streamlit's default sidebar page nav — we use a top bar */
            [data-testid="stSidebarNav"] {{ display: none; }}
            .stApp {{ {app_bg} color: #E8EEF7; }}
            /* let the arena photo show through the top header strip */
            [data-testid="stHeader"] {{ background: transparent !important; }}
            /* hide the auto anchor-link icon that appears on hover over headings */
            [data-testid="stHeaderActionElements"] {{ display: none !important; }}
            h1 a[href^="#"], h2 a[href^="#"], h3 a[href^="#"],
            h4 a[href^="#"], h5 a[href^="#"], h6 a[href^="#"] {{ display: none !important; }}
            h1, h2, h3, h4 {{ color: #F4F7FB; font-weight: 700; }}
            [data-testid="stSidebar"] {{ background-color: {BLUE}; }}
            [data-testid="stSidebar"] * {{ color: #ffffff !important; }}
            /* sidebar widgets: white control, dark legible text (regardless of theme) */
            [data-testid="stSidebar"] [data-baseweb="select"] > div,
            [data-testid="stSidebar"] [data-baseweb="input"] {{ background: #ffffff !important; }}
            [data-testid="stSidebar"] [data-baseweb="select"],
            [data-testid="stSidebar"] [data-baseweb="select"] div,
            [data-testid="stSidebar"] [data-baseweb="input"] input,
            [data-testid="stSidebar"] input {{ color: {BLUE} !important; }}
            /* but multiselect pills stay white-on-orange */
            [data-testid="stSidebar"] [data-baseweb="tag"],
            [data-testid="stSidebar"] [data-baseweb="tag"] * {{ color: #ffffff !important; }}
            /* dropdowns: discreet down-chevron, and not typeable (click to open only) */
            [data-testid="stSidebar"] [data-baseweb="select"] svg {{ fill: #9aa6b2 !important; }}
            [data-testid="stSidebar"] [data-baseweb="tag"] svg {{ fill: #ffffff !important; }}
            [data-testid="stSidebar"] [data-baseweb="select"] input:not([aria-label*="Scout this team"]) {{
                pointer-events: none !important; caret-color: transparent !important;
            }}
            [data-testid="stMetricValue"] {{ color: {ORANGE}; }}

            /* top navigation bar — pinned into Streamlit's fixed header strip */
            .hub-topbar {{
                position: fixed; top: 0; left: 316px; height: 60px;
                display: flex; align-items: center; gap: 1.1rem;
                z-index: 999991; padding: 0; margin: 0;
            }}
            .hub-wordmark {{
                font-weight: 800; letter-spacing: .04em; color: {BLUE};
                font-size: 1.02rem; white-space: nowrap;
            }}
            .hub-nav {{ display: flex; gap: .4rem; flex-wrap: wrap; }}
            /* section headers / labels with a leading line-icon */
            h3.hub-section {{ display: flex; align-items: center; }}
            .hub-iconlabel {{
                display: flex; align-items: center; margin: 0 0 .35rem 0;
                color: #F4F7FB; font-size: 1rem;
            }}
            /* player cards (key players) */
            .pcard {{
                background: #fff; border: 1px solid #e2e2e2; border-radius: 8px;
                padding: .7rem .85rem; margin-bottom: .6rem;
            }}
            .pc-head {{ display: flex; align-items: center; gap: .7rem; margin-bottom: .6rem; }}
            .pc-avatar {{
                border-radius: 50%; display: flex; align-items: center;
                justify-content: center; color: #fff; font-weight: 800; flex: none;
            }}
            .pc-name {{ font-weight: 700; color: {BLUE}; font-size: 1rem; line-height: 1.15; }}
            .pc-sub {{ color: #777; font-size: .8rem; }}
            .pc-stats {{ display: flex; gap: .4rem; }}
            .pc-stat {{
                flex: 1; background: {LIGHT}; border-radius: 7px;
                padding: .35rem .2rem; text-align: center;
            }}
            .pc-v {{ display: block; font-weight: 700; color: {BLUE}; font-size: .95rem; }}
            .pc-k {{
                display: block; color: #888; font-size: .62rem;
                letter-spacing: .03em; text-transform: uppercase;
            }}
            /* KPI cards (dark navy) */
            .kpi {{
                background: {BLUE}; border-radius: 8px; padding: .7rem .85rem;
                height: 100%; margin-bottom: .65rem;
            }}
            .kpi-label {{
                color: #cdd6e4; font-size: .76rem; font-weight: 600;
                text-transform: uppercase; letter-spacing: .03em; margin-bottom: .25rem;
            }}
            .kpi-row {{ display: flex; align-items: baseline; gap: .4rem; flex-wrap: wrap; }}
            .kpi-value {{ color: {ORANGE}; font-size: 1.65rem; font-weight: 800; line-height: 1.1; }}
            .kpi-badge {{
                background: #e6f4ea; color: #1e7e34; font-size: .7rem; font-weight: 700;
                padding: .1rem .42rem; border-radius: 999px; white-space: nowrap;
            }}
            .kpi-note {{ color: #9fb0c9; font-size: .74rem; font-weight: 600; }}
            .kpi-sub {{ color: #9fb0c9; font-size: .72rem; margin-top: .25rem; }}
            /* white card around every Plotly chart. overflow:hidden clips the
               square-cornered Plotly canvas to the rounded card so the corners
               actually look rounded (and repaint cleanly on scroll). */
            [data-testid="stPlotlyChart"] {{
                background: #ffffff; border: 1px solid #e7e7e7; border-radius: 12px;
                padding: .7rem 1rem; overflow: hidden;
            }}
            /* pie / donut charts float transparent on the dark theme (no white card).
               Use .slice (only present in pies) — .pielayer exists in every chart. */
            [data-testid="stPlotlyChart"]:has(.slice) {{
                background: transparent; border: none; padding: 0; overflow: visible;
            }}
            /* white-card HTML tables — static (no inner scroll), compact text */
            .wt-card {{
                background: #fff; border: 1px solid #e2e2e2; border-radius: 8px;
                padding: .2rem .4rem;
            }}
            table.wt {{ width: 100%; border-collapse: collapse; font-size: .76rem; color: {BLUE}; }}
            table.wt th {{
                text-align: left; background: #fff;
                color: #6a7385; font-weight: 700; font-size: .64rem;
                text-transform: uppercase; letter-spacing: .02em;
                padding: .32rem .5rem; border-bottom: 2px solid #eee; white-space: nowrap;
            }}
            table.wt td {{
                padding: .28rem .5rem; border-bottom: 1px solid #f2f2f2;
                white-space: nowrap; color: {BLUE};
            }}
            table.wt tbody tr:last-child td {{ border-bottom: none; }}
            table.wt tbody tr:hover td {{ background: #fff7f2; }}
            .wt-bar {{
                position: relative; background: #eef0f3; border-radius: 6px;
                height: 18px; min-width: 90px;
            }}
            .wt-bar-fill {{
                position: absolute; left: 0; top: 0; bottom: 0;
                background: {ORANGE}; border-radius: 6px;
            }}
            .wt-bar-txt {{
                position: relative; padding-left: .45rem; font-weight: 700;
                font-size: .75rem; line-height: 18px; color: {BLUE};
            }}
            /* sidebar brand logo (top-left, above the filters) */
            .hub-sidelogo {{
                display: flex; align-items: center; gap: .6rem;
                padding: .2rem 0 .4rem 0; margin-bottom: .2rem;
                border-bottom: 1px solid rgba(255,255,255,.15);
            }}
            .hub-side-word {{
                color: #ffffff; font-weight: 800; letter-spacing: .03em;
                font-size: .9rem; line-height: 1.1;
            }}
            /* nav buttons: identical size whether active or not — only colour changes */
            .hub-link {{
                display: inline-flex; align-items: center; gap: .4rem;
                border: 1px solid #d7d7d7; border-radius: 8px;
                padding: .4rem .8rem; background: #ffffff;
                color: {BLUE} !important; font-weight: 600; font-size: .9rem;
                text-decoration: none !important; white-space: nowrap; line-height: 1.2;
            }}
            .hub-link:hover {{
                border-color: {ORANGE}; background: #fff4ee;
                text-decoration: none !important;
            }}
            .hub-link.active {{
                background: {ORANGE}; border-color: {ORANGE};
                color: #ffffff !important;
            }}

            /* page title bar */
            .hub-banner {{
                border-left: 6px solid {ORANGE};
                background: #ffffff; border-radius: 8px;
                padding: .8rem 1.1rem; margin: .3rem 0 1.2rem 0;
                box-shadow: 0 1px 4px rgba(0,0,0,.06);
            }}
            .hub-banner h1 {{ margin: 0; font-size: 1.55rem; color: {BLUE}; }}
            .hub-banner p {{ margin: .25rem 0 0 0; color: #555; font-size: .95rem; }}
            .stDataFrame {{ border: 1px solid #e2e2e2; border-radius: 8px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _top_nav(active: str) -> None:
    links = "".join(
        f'<a class="hub-link{" active" if label == active else ""}" '
        f'href="{url}" target="_self">'
        f'{icon(ic, "currentColor", 16, margin="0")}{label}</a>'
        for label, url, ic in NAV
    )
    st.markdown(
        f'<div class="hub-topbar"><nav class="hub-nav">{links}</nav></div>',
        unsafe_allow_html=True,
    )


# Sidebar selects whose label contains any of these stay searchable (typeable);
# all others are click-to-open only.
_SEARCHABLE_SELECTS = ["Scout this team"]


def _lock_select_typing() -> None:
    """Make sidebar dropdowns click-to-open only (no search/typing), except the
    ones in ``_SEARCHABLE_SELECTS`` (e.g. the 365-team team picker).

    Streamlit/BaseWeb selects are searchable: opening one focuses a text input you
    can type in. There's no Python flag to turn that off, so we flag the inputs
    ``readonly`` from the parent document and re-apply on every re-render.
    """
    allow = ",".join(repr(s) for s in _SEARCHABLE_SELECTS)
    components.html(
        f"""
        <script>
        const doc = window.parent.document;
        const ALLOW = [{allow}];
        function searchable(i) {{
          const l = i.getAttribute('aria-label') || '';
          return ALLOW.some(s => l.indexOf(s) !== -1);
        }}
        function lock() {{
          doc.querySelectorAll(
            '[data-testid="stSidebar"] [data-baseweb="select"] input'
          ).forEach(i => {{ if (!searchable(i) && !i.readOnly) i.readOnly = true; }});
        }}
        lock();
        new MutationObserver(lock).observe(doc.body, {{childList: true, subtree: true}});
        </script>
        """,
        height=0,
    )


def page_setup(title: str, subtitle: str = "", nav: str = "Home",
               filters_label: str = "Filters",
               sidebar_state: str = "expanded") -> None:
    """Standard page config + Illinois branding. Call first on every page.

    Renders the top navigation bar and the page title banner, and (when
    ``filters_label`` is set) titles the sidebar. Pages with no filters (Home)
    pass ``filters_label=""`` and ``sidebar_state="collapsed"``.
    """
    st.set_page_config(page_title=f"{title} · Illinois Hoops Hub", layout="wide",
                       initial_sidebar_state=sidebar_state)
    _install_plot_template()
    _inject_css()
    _top_nav(nav)
    st.markdown(
        f'<div class="hub-banner"><h1>{title}</h1>'
        + (f'<p>{subtitle}</p>' if subtitle else "")
        + "</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f'<div class="hub-sidelogo">{block_i(50, outline="#FFFFFF")}'
        f'<span class="hub-side-word">ILLINOIS<br>HOOPS HUB</span></div>',
        unsafe_allow_html=True,
    )
    if filters_label:
        st.sidebar.markdown(f"## {filters_label}")
    _lock_select_typing()
