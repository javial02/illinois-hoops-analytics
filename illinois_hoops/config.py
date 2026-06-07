"""Project-wide configuration: the team we build for, branding, and the
current season. Centralised so every module and the Streamlit app agree."""

from __future__ import annotations

# The program this tool is built for. Change TEAM to retarget the whole app.
TEAM = "Illinois"
CONFERENCE = "B10"  # BartTorvik conference code for the Big Ten

# Season to analyse. BartTorvik uses the season-ending year, so the 2025-26
# season is "2026".
DEFAULT_SEASON = 2026

# Illinois brand colours (Illini Orange / Industrial Blue) for the UI.
ORANGE = "#FF5F05"
BLUE = "#13294B"
LIGHT = "#F5F5F5"

# Power-conference codes — used to flag "level of competition" when judging
# whether a mid-major transfer's production should translate up.
POWER_CONFS = {"B10", "B12", "BE", "ACC", "SEC", "P12"}

# Map BartTorvik's granular position labels onto three roster buckets so we can
# reason about positional need without 12 micro-categories.
POSITION_BUCKETS = {
    "Pure PG": "Guard",
    "Scoring PG": "Guard",
    "Combo G": "Guard",
    "Wing G": "Wing",
    "Wing F": "Wing",
    "Stretch 4": "Forward",
    "PF/C": "Big",
    "C": "Big",
}


def bucket_position(pos: str) -> str:
    """Collapse a BartTorvik position string into Guard / Wing / Forward / Big."""
    return POSITION_BUCKETS.get((pos or "").strip(), "Wing")
