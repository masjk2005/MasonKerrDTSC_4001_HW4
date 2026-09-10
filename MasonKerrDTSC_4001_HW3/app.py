#!/usr/bin/env python
# coding: utf-8

# In[48]:


import sys
import streamlit as st

# In[8]:

import sportsdataverse.cfb as cfb
import pandas as pd
import altair as alt

# In[7]:

#data
raw_pbp = cfb.load_cfb_pbp(seasons=2025, return_as_pandas=True)

#FBS only
fbs_teams = ['ACC', 'Big 12', 'Big Ten', 'SEC','FBS Independents', 'American Athletic', 'Conference USA', 'MAC', 'Mountain West', 'Sun Belt', 'Pac-12']
schedule = cfb.load_cfb_schedule(seasons=[2025], return_as_pandas=True)

home_conferences = schedule[
    ['game_id', 'season', 'home_id', 'home_conference']
].rename(columns={'home_id': 'pos_team_id', 'home_conference': 'conference'})
away_conferences = schedule[
    ['game_id', 'season', 'away_id', 'away_conference']
].rename(columns={'away_id': 'pos_team_id', 'away_conference': 'conference'})
conference_lookup = pd.concat([home_conferences, away_conferences], ignore_index=True)

fbs_pbp_all = raw_pbp.merge(
    conference_lookup,
    on=['game_id', 'season', 'pos_team_id'],
    how='left',
    validate='many_to_one'
)
fbs_pbp_all = fbs_pbp_all[fbs_pbp_all['conference'].isin(fbs_teams)].copy()

fbs_pbp = raw_pbp.merge(
    conference_lookup,
    on=['game_id', 'season', 'pos_team_id'],
    how='left',
    validate='many_to_one' #prevents duplicate rows
)
fbs_pbp = fbs_pbp[fbs_pbp['conference'].isin(fbs_teams)].copy()

# In[43]:

#team abbreviations and colors using Saiem Gilani's dataset on GitHub (from downloaded ZIP file)
from pathlib import Path
from zipfile import ZipFile
import re
import unicodedata
import pandas as pd
from difflib import get_close_matches

# Change this to your downloaded GitHub ZIP file
ZIP_PATH = Path(r"C:\Users\masjk\Downloads\c6596f0e1c8b148daabc2b7f1e6f6add-915d48a38d56a90a02d20856faf428408eeff131.zip")

# Find CSV files inside the ZIP
with ZipFile(ZIP_PATH) as archive:
    csv_files = [
        name for name in archive.namelist()
        if name.lower().endswith(".csv")
    ]
    print("CSV files found:", csv_files)
    # Usually the team file is the only CSV or contains "team" in its name
    team_file = next(
        (name for name in csv_files if "team" in name.lower()),
        csv_files[0],
    )
    with archive.open(team_file) as file:
        teams_data = pd.read_csv(file)

#account for different conference names in zip and fbs_teams dataset
conference_aliases = {
    "Mid-American": "MAC",
}

teams_data["conference_standard"] = (
    teams_data["conference"]
    .replace(conference_aliases)
)

#account for different team names (App, UMass, Minnesota)
team_name_aliases = {
    "App State": "Appalachian State",
    "Minnesota Duluth": "Minnesota",
    "Massachusetts": "UMass",
}

schedule["home_team"] = schedule["home_team"].replace(team_name_aliases)
schedule["away_team"] = schedule["away_team"].replace(team_name_aliases)

schedule_team_names = sorted(
    set(schedule["home_team"].dropna())
    | set(schedule["away_team"].dropna())
)

teams_d1 = teams_data[
    teams_data["conference_standard"].isin(fbs_teams)
].copy()

# In[ ]:

#Teams (finding right column[s] to correctly match all teams)
def normalize_team_name(value):
    value = unicodedata.normalize("NFKD", str(value))
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]", "", value)
    return value

# Possible name columns in the downloaded dataset
name_columns = [
    col for col in teams_d1.columns
    if any(term in col.lower() for term in [
        "school", "mascot", "abbreviation", "alt_name", "alt_name2", "alt_name3"
    ])
]

# Create lookup from every available name to the team's row
team_lookup = {}

for _, row in teams_d1.iterrows():
    for column in name_columns:
        value = row.get(column)

        if pd.notna(value) and str(value).strip():
            key = normalize_team_name(value)
            team_lookup.setdefault(key, row)

# Team names appearing in the schedule
schedule_team_names = sorted(
    set(schedule["home_team"].dropna())
    | set(schedule["away_team"].dropna())
)

matched_teams = {}
unmatched_teams = []

for team_name in schedule_team_names:
    key = normalize_team_name(team_name)

    if key in team_lookup:
        matched_teams[team_name] = team_lookup[key]
    else:
        unmatched_teams.append(team_name)

print("Matched teams:", len(matched_teams))
print("Unmatched teams:", unmatched_teams)

#delaware, jax state, jmu, kenn state, sam houston, and one more(?) are all missing

# In[ ]:

#Website Creation using "Stock Peer Analysis Dashboard" Streamlit design as a template 

#week dropdown that lists all games that week 
#team dropdown that lists that team's yearlong results

#selection creates chart below (starts as blank until selection is made)

#need to scrape team's primary colors, maybe logos, for chart and team abbreviation

#plot wp using function that with one single line that if it dips into either team's half, the color and shading under line changes to that team's color and a vertical line for each score change

# In[46]:

#title
st.set_page_config(
    page_title="Win Probability Dashboard",
    page_icon="🏈",
    layout="wide",
)

#building schedule to find teams/weeks
season_schedule = schedule.copy()
season_schedule = season_schedule[
    season_schedule["home_conference"].isin(fbs_teams)
    & season_schedule["away_conference"].isin(fbs_teams)
].copy()

# Build team list from home and away teams
teams = sorted(
    set(season_schedule["home_team"].dropna())
    | set(season_schedule["away_team"].dropna())
)

#Select team dropdown
team = st.selectbox("Select team", teams)

# Games involving the selected team
team_games = season_schedule[
    (season_schedule["home_team"] == team)
    | (season_schedule["away_team"] == team)
].copy()

# Select week and opponent
week_options = {}
for _, row in team_games.iterrows():
    opponent = (
        row["away_team"]
        if row["home_team"] == team
        else row["home_team"]
    )
    week_options[row["game_id"]] = f'Week {int(row["week"])} - vs {opponent}'

selected_game_id = st.selectbox(
    "Select week",
    options=list(week_options.keys()),
    format_func=lambda game_id: week_options[game_id],
)

selected_game = team_games[
    team_games["game_id"] == selected_game_id
].iloc[0]


#adding space?
cols = st.columns([3, 1])

#add cell for chart
right_cell = cols[0].container(
    border=True, height="stretch", vertical_alignment="center"
)

def get_team_info(team_name):
    key = normalize_team_name(team_name)
    team_row = team_lookup.get(key)

    if team_row is not None:
        return {
            "abbreviation": team_row.get("abbreviation"),
            "logo_url": team_row.get("logo"),
            "primary_color": team_row.get("color"),
            "secondary_color": team_row.get("alt_color"),
        }
    else:
        return {
            "abbreviation": None,
            "logo_url": None,
            "primary_color": None,
            "secondary_color": None,
        }


home_team = selected_game["home_team"]
away_team = selected_game["away_team"]

home_info = get_team_info(home_team)
away_info = get_team_info(away_team)

home_score = selected_game.get("home_points", selected_game.get("home_score", 0))
away_score = selected_game.get("away_points", selected_game.get("away_score", 0))

#add cell to left of chart that displays team abbreviation/logo and score
left_cell = cols[1].container(
    border=True, height="stretch", vertical_alignment="center"
)
with left_cell:
    if pd.notna(home_info["logo_url"]):
        st.image(home_info["logo_url"], width=75)

    st.metric(
        label=home_info["abbreviation"] or home_team,
        value=int(home_score) if pd.notna(home_score) else 0,
    )

    st.divider()

    if pd.notna(away_info["logo_url"]):
        st.image(away_info["logo_url"], width=75)

    st.metric(
        label=away_info["abbreviation"] or away_team,
        value=int(away_score) if pd.notna(away_score) else 0,
    )

# In[50]:


print([
    column for column in fbs_pbp_all.columns
    if "wp" in column.lower() or "prob" in column.lower()
])

# In[52]:


#plot Win Prob using altair

game_pbp = fbs_pbp_all[fbs_pbp_all["game_id"] == selected_game_id].copy()
game_pbp = game_pbp.dropna(subset=["home_wp_after"]).reset_index(drop=True)

# Color/shading depends on which half of the probability scale is active
game_pbp["probability_half"] = game_pbp["home_wp_after"].ge(0.5).map({
    True: "Home",
    False: "Away",
})
game_pbp["home_shading_wp"] = game_pbp["home_wp_after"].where(
    game_pbp["home_wp_after"] >= 0.5
)
game_pbp["away_shading_wp"] = game_pbp["home_wp_after"].where(
    game_pbp["home_wp_after"] < 0.5
)

game_pbp["quarter_change"] = game_pbp["period"].ne(
    game_pbp["period"].shift()
)
previous_scores_exist = (
    game_pbp["homeScore"].shift().notna()
    & game_pbp["awayScore"].shift().notna()
)
game_pbp["home_score_change"] = previous_scores_exist & game_pbp[
    "homeScore"
].ne(game_pbp["homeScore"].shift())
game_pbp["away_score_change"] = previous_scores_exist & game_pbp[
    "awayScore"
].ne(game_pbp["awayScore"].shift())
game_pbp["score_change"] = (
    game_pbp["home_score_change"] | game_pbp["away_score_change"]
)
quarter_lines = game_pbp[
    game_pbp["quarter_change"] & game_pbp["period"].between(1, 4)
][["game_play_number", "period"]].drop_duplicates()
quarter_lines["quarter_label"] = "Q" + quarter_lines["period"].astype(int).astype(str)
score_lines = game_pbp[game_pbp["score_change"]][
    ["game_play_number", "home_score_change", "scoringType.name"]
].drop_duplicates()
score_lines["scoring_team"] = score_lines["home_score_change"].map({
    True: "Home",
    False: "Away",
})
score_lines["score_label"] = score_lines["scoringType.name"].map({
    "touchdown": "TD",
    "field-goal": "FG",
    "safety": "SAF",
})
score_labels = score_lines[score_lines["score_label"].notna()]

home_color = home_info["primary_color"]
away_color = away_info["primary_color"]
if pd.isna(home_color):
    home_color = "#1f77b4"
if pd.isna(away_color):
    away_color = "#d62728"
color_scale = alt.Scale(
    domain=["Home", "Away"],
    range=[home_color, away_color],
)

base = (
    alt.Chart(game_pbp)
    .encode(
        x=alt.X(
            "game_play_number:Q",
            title="Progress of game",
            axis=alt.Axis(labels=False, ticks=False),
        ),
        y=alt.Y(
            "home_wp_after:Q",
            title=f"{home_team} win probability",
            scale=alt.Scale(domain=[0, 1]),
            axis=alt.Axis(format="%"),
        ),
    )
)
away_area = base.mark_area(
    opacity=0.25,
    line=False,
).encode(
    y=alt.Y("away_shading_wp:Q"),
    color=alt.value(away_color),
    y2=alt.datum(0.5)
)

home_area = base.mark_area(
    opacity=0.25,
    line=False,
).encode(
    y=alt.Y("home_shading_wp:Q"),
    color=alt.value(home_color),
    y2=alt.datum(0.5)
)

line = base.mark_line(stroke="#4a4a4a", strokeWidth=3)

midpoint = alt.Chart(
    pd.DataFrame({"probability": [0.5]})
).mark_rule(
    color="gray",
    strokeDash=[4, 4],
).encode(
    y="probability:Q"
)

score_rules = alt.Chart(score_lines).mark_rule(
    opacity=0.8,
    strokeWidth=1,
).encode(
    x="game_play_number:Q",
    color=alt.Color(
        "scoring_team:N",
        scale=color_scale,
        legend=None,
    ),
)

quarter_rules = alt.Chart(quarter_lines).mark_rule(
    color="#4a4a4a",
    opacity=0.9,
    strokeDash=[2, 2],
    strokeWidth=2,
).encode(
    x="game_play_number:Q"
)

quarter_labels = alt.Chart(quarter_lines).mark_text(
    color="#4a4a4a",
    align="left",
    baseline="bottom",
    dx=4,
    dy=-4,
).encode(
    x="game_play_number:Q",
    y=alt.datum(0.03),
    text="quarter_label:N",
)

home_score_labels = score_labels[score_labels["scoring_team"] == "Home"]
away_score_labels = score_labels[score_labels["scoring_team"] == "Away"]

home_score_labels_chart = alt.Chart(home_score_labels).mark_text(
    align="left",
    baseline="top",
    dx=4,
    dy=4,
).encode(
    x="game_play_number:Q",
    y=alt.datum(0.97),
    text="score_label:N",
    color=alt.Color(
        "scoring_team:N",
        scale=color_scale,
        legend=None,
    ),
)

away_score_labels_chart = alt.Chart(away_score_labels).mark_text(
    align="left",
    baseline="bottom",
    dx=4,
    dy=-4,
).encode(
    x="game_play_number:Q",
    y=alt.datum(0.08),
    text="score_label:N",
    color=alt.Color(
        "scoring_team:N",
        scale=color_scale,
        legend=None,
    ),
)

chart = (
    (
        away_area
        + home_area
        + line
        + midpoint
        + score_rules
        + quarter_rules
        + quarter_labels
        + home_score_labels_chart
        + away_score_labels_chart
    )
    .properties(
        height=400,
        title=f"{away_team} at {home_team}",
    )
)

with right_cell:
    st.altair_chart(chart, use_container_width=True)

# with right_cell:
#     st.altair_chart(
#         alt.Chart(
#             normalized.reset_index().melt(
#                 id_vars=["Date"], var_name="Stock", value_name="Normalized price"
#             )
#         )
#         .mark_line()
#         .encode(
#             alt.X("Date:T"),
#             alt.Y("Normalized price:Q").scale(zero=False),
#             alt.Color("Stock:N"),
#         )
#         .properties(height=400)
#     )
