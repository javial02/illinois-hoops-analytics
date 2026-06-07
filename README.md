# Illinois Hoops Analytics Hub

A public-data **front-office toolkit for college basketball** — transfer-portal
targeting and roster construction, plus opponent scouting, in one interactive web app.

Built for the **University of Illinois Men's Basketball Analytics Internship**.

- **Live app:** https://illinois-hoops-analytics-m5lhhuuwjghhdwqza5x67o.streamlit.app/
- **Write-up & methodology:** [`docs/Illinois_Hoops_Submission.pdf`](docs/Illinois_Hoops_Submission.pdf)

---

## What it does

| Module | Question | What it does |
|---|---|---|
| **Transfer Portal** | Who should we sign, and how does it change us? | Profiles our roster and holes, ranks transfer candidates by **projected high-major value × fit** to our needs, and includes a **fit simulator** (set departures and arrivals → a before/after skill radar). |
| **Opponent Scouting** | What is this team's identity and how do we beat them? | An auto-generated **four-factor** report, key players, strengths/weaknesses and **keys to the game** for any of 365 teams. |

Every score is **explainable** — no black boxes.

## Data

All from **[BartTorvik](https://barttorvik.com)** (free, opponent-adjusted public
data), via three endpoints (player-season, team-season and per-game), cached
locally in `data/raw/`. Uses the latest completed season, **2025-26**. Column
layouts were reverse-engineered and validated against known players and teams;
see the write-up for details.

## Tech stack

Python 3.12 · `uv` · `pandas` · `numpy` · **Streamlit** · **Plotly** · `pillow`

## Project layout

```
illinois_hoops/        core package (all logic, reusable and testable)
  data.py              fetch + cache + parse BartTorvik
  portal.py            transfer value/fit model + roster needs
  scouting.py          four-factor opponent reports
  roster.py            roster profiling + transfer-addition simulator
  config.py            target team, branding, position buckets
  appkit.py            shared Streamlit UI, theme, charts and helpers
app/
  Home.py              landing page (Illinois snapshot + national landscape)
  pages/               Transfer Portal · Opponent Scouting
data/raw/              cached source data (committed for instant deploys)
docs/                  submission write-up & methodology (PDF)
```

## Run locally

```bash
# with uv (recommended)
uv sync
uv run streamlit run app/Home.py

# or with pip
pip install -r requirements.txt
streamlit run app/Home.py
```

Then open http://localhost:8501.

To refresh the cached data with the latest from BartTorvik:

```bash
uv run python -c "from illinois_hoops import data; \
data.fetch_players(refresh=True); data.fetch_teams(refresh=True); data.fetch_games(refresh=True)"
```

## Deployment

The app is hosted for free on **Streamlit Community Cloud** at the live link above;
every push to `main` redeploys it automatically. To deploy your own copy: push the
repo to GitHub, then at [share.streamlit.io](https://share.streamlit.io) create an
app pointing at it with main file `app/Home.py`. Streamlit Cloud installs
`requirements.txt` automatically, and the committed cache means it starts
immediately (no hosting or domain cost).

## Notes and limitations

The board ranks *potential* targets; public data has no live portal-entrant feed
(joining one is a simple filter). The competition-translation multiplier is a
transparent, tunable assumption. See the write-up for the full methodology and
limitations.

---

*Educational project. Data © barttorvik.com.*
