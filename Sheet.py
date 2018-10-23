# coding: utf-8

import pandas as pd
import os
import time
import datetime
import time
import numpy as np
import webbrowser

import gspread
import gspread_dataframe as gd
import datetime
import json
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)
# today = time.strftime("%m/%d/%Y")
# today = time.strftime("%Y-%m-%d")
# today = datetime.strptime(today, "%m/%d/%Y")
# from datetime import date
# from datetime import datetime
# from dateutil.parser import parse

# from DailyModelScrape import get_bbm
# bbm_df = get_bbm()
# today = time.strftime("%m/%d/%Y")


# Set the directory and read in the current Kostya Plus Minus, Team Name Crosswalk, and the 2019 Schedule

os.chdir("C:/Users/kmedvedovsky/Downloads/box/Personal/Python/Projects/NBA/Win Projections")
kpm = pd.read_csv("kpm.csv")
team_crosswalk = pd.read_csv("team_name_crosswalk.csv")
schedule = pd.read_csv("2019_Schedule.csv", parse_dates=['Date', 'v_last_game_date', 'h_last_game_date'])

# Set the Databaseback back to this sheet
os.chdir("C:/Users/kmedvedovsky/Downloads/box/Personal/Python/Projects/NBA/Sheet/Databases")

# Read in the full season's worth of minutes

bbm_minutes = pd.read_excel("2019_bbm_minutes.xlsx", sheet_name="all", parse_dates=['Date'])
bbm_minutes.head()

# Rename a couple columns for better processing.

bbm_minutes.rename(columns={'id': 'bbm_id'}, inplace=True)
bbm_minutes['game_date'] = pd.to_datetime('1899-12-30') + pd.to_timedelta(bbm_minutes.Date, 'D')

# Merge the season long ratings with the season-long KPM ratings. This will need to be fixed to create new KPM out-of-sample ratings.

daily_ratings = pd.merge(bbm_minutes, kpm[["bbm_id", "oKPM", "dKPM"]], on="bbm_id")

# Check if there are any missing players:
missing = daily_ratings[pd.isnull(daily_ratings.oKPM)]

if len(missing.index) > 0:
    print(missing)
else:
    print("all players found")

# Fill in any missing players for now.

daily_ratings["oKPM"] = daily_ratings["oKPM"].fillna(-1.2)
daily_ratings["dKPM"] = daily_ratings["dKPM"].fillna(-0.3)

# Create offensive and defensive values.
daily_ratings["oValue"] = daily_ratings["minutes"] * daily_ratings["oKPM"] / 48
daily_ratings["dValue"] = daily_ratings["minutes"] * daily_ratings["dKPM"] / 48
summary = daily_ratings[["Name", "game_date", "oKPM", "dKPM", "oValue", "dValue", "Inj", "minutes"]]
daily_ratings.head()

# Pull out the odds forcast

odds = daily_ratings[["team_game_id", "odds_spread", "odds_total", "game_date"]]

# Drop dupes since they appear on a player level.
odds = odds.drop_duplicates(subset=["team_game_id", "odds_spread"], keep="first")
# odds.rename(columns={'BetterDT': 'Date'}, inplace=True)
odds.head()

# Create different team ratings by date.

team_offense = daily_ratings.groupby(['team_game_id'])['oValue'].sum().reset_index()
team_defense = daily_ratings.groupby(['team_game_id'])['dValue'].sum().reset_index()
team_minutes = daily_ratings.groupby(['team_game_id'])['minutes'].sum().reset_index()

team_offense.rename(columns={'oValue': 'oRTG'}, inplace=True)
team_defense.rename(columns={'dValue': 'dRTG'}, inplace=True)

team_offense.head()

# Merge the three, and get average values. This gives ratings per 100 possessions now.

team_ratings = pd.merge(team_minutes, team_offense, on="team_game_id")
team_ratings = pd.merge(team_ratings, team_defense, on="team_game_id")
# team_ratings["oRTG"]=team_ratings["oRTG"]/team_ratings["minutes"]*5
# team_ratings["dRTG"]=team_ratings["dRTG"]/team_ratings["minutes"]*5
team_ratings["net"] = team_ratings["oRTG"] + team_ratings["dRTG"]
team_ratings.head()

# Split the game IDs to get the team names

team_ratings['team'] = team_ratings.team_game_id.str.split('_').str.get(0)
team_ratings['date'] = team_ratings.team_game_id.str.split('_').str.get(1)

# Merge in the basketball-reference team names and the odds

team_ratings = pd.merge(team_ratings, team_crosswalk[["bref_name", "bbm_abr"]], left_on="team", right_on="bbm_abr")
team_ratings = pd.merge(team_ratings, odds[["team_game_id", "odds_spread", "odds_total", "game_date"]],
                        on="team_game_id", how="left")

# team_ratings.drop(["bbm_abr","team"],axis=1,inplace=True)

# Parse the odds and the total
team_ratings['favorite'] = team_ratings.odds_spread.str.split(' by ').str.get(0)
team_ratings['fave_by'] = team_ratings.odds_spread.str.split(' by ').str.get(1)

# Turn the game date into a string.
team_ratings['bref_game_id'] = team_ratings['bref_name'] + "_" + team_ratings.game_date.dt.strftime("%m/%d/%Y")
team_ratings.rename(columns={'date': 'numeric_date'}, inplace=True)
team_ratings.to_csv("tr.csv")
team_ratings.head()

# Merge onto the schedule

predictions = schedule.copy()

# Create a game_id field to map the visitor data to

predictions['v_bref_game_id'] = predictions['Visitor/Neutral'] + "_" + predictions.Date.dt.strftime("%m/%d/%Y")

predictions = pd.merge(predictions, team_ratings[
    ["bref_game_id", "oRTG", "dRTG", "favorite", "fave_by", "odds_total", "numeric_date"]], left_on="v_bref_game_id",
                       right_on="bref_game_id", how="left")

# Rename columns to make clear they're visitor data.
predictions.rename(columns={'oRTG': 'v_oRTG'}, inplace=True)
predictions.rename(columns={'dRTG': 'v_dRTG'}, inplace=True)
predictions.rename(columns={'net': 'v_net'}, inplace=True)
predictions.drop(["bref_game_id"], axis=1, inplace=True)

predictions['h_bref_game_id'] = predictions['Home/Neutral'] + "_" + predictions.Date.dt.strftime("%m/%d/%Y")

predictions = pd.merge(predictions, team_ratings[["bref_game_id", "oRTG", "dRTG", "bbm_abr"]], left_on="h_bref_game_id",
                       right_on="bref_game_id", how="left")

# Rename columns to make clear they're home data.
predictions.rename(columns={'oRTG': 'h_oRTG'}, inplace=True)
predictions.rename(columns={'dRTG': 'h_dRTG'}, inplace=True)
predictions.rename(columns={'net': 'h_net'}, inplace=True)
predictions.rename(columns={'bbm_abr': 'h_bbm_abr'}, inplace=True)
predictions.drop(["bref_game_id"], axis=1, inplace=True)

# Convert to numeric
predictions['fave_by'] = predictions.fave_by.astype(float)
predictions['numeric_date'] = predictions.numeric_date.astype(float)

# Determine if the home team is the favorite, and rephrase the spread in correct spread terms

predictions["home_fav"] = predictions["h_bbm_abr"] == predictions["favorite"]
predictions["spread"] = predictions["fave_by"] - predictions["home_fav"] * predictions["fave_by"] * 2

predictions.head()

# Add in the game predictions

# Regress the spreads a bit. Play with this.
spread_regress = 0.88

# Set some league variables which will need to get team-specific eventually
lg_pace = 102
lg_oRating = 109.5
lg_hca = 2.394451

lg_h_b2b = 1.441175
lg_v_b2b = 1.980115

# Adjust for travel and rest

predictions["h_oRTG"] = predictions["h_oRTG"] - predictions["HCA_h_B2B"] * lg_h_b2b / 2
predictions["h_dRTG"] = predictions["h_dRTG"] - predictions["HCA_h_B2B"] * lg_h_b2b / 2
predictions["v_oRTG"] = predictions["v_oRTG"] - predictions["HCA_v_B2B"] * lg_v_b2b / 2
predictions["v_dRTG"] = predictions["v_dRTG"] - predictions["HCA_v_B2B"] * lg_v_b2b / 2

# Predict the scores
predictions["h_score"] = (lg_oRating + (predictions["h_oRTG"] - predictions["v_dRTG"])) * lg_pace / 100 + lg_hca / 2
predictions["v_score"] = (lg_oRating + (predictions["v_oRTG"] - predictions["h_dRTG"])) * lg_pace / 100 - lg_hca / 2

# Predict the spread and total
predictions["xSpread"] = predictions["v_score"] - predictions["h_score"]
predictions["xTotal"] = predictions["v_score"] + predictions["h_score"]

# Compare to the actual spread and total and make picks.
predictions["spread_delta"] = predictions["xSpread"] - predictions["spread"]
predictions["pick_home"] = predictions["spread_delta"] < 0
predictions["total_delta"] = predictions["xTotal"] - predictions["odds_total"]
predictions["pick_over"] = predictions["xTotal"] > predictions["odds_total"]

predictions.to_csv("full_season_predictions.csv")
predictions.head()

# Add in some spread delta stuff

predictions["abs_delta"] = predictions["spread_delta"].abs()

# Get an absolute value for the spread delta
predictions["abs_delta"] = predictions["spread_delta"].abs()

# Get an absolute value for the total delta
predictions["abs_total_delta"] = predictions["total_delta"].abs()
predictions = predictions.sort_values(by=["abs_delta"], ascending=False)

# Add in what the actual picks are
predictions['spread_bet'] = np.where(predictions['pick_home'] == True, predictions["Home/Neutral"],
                                     predictions["Visitor/Neutral"])
predictions['total_bet'] = np.where(predictions['pick_over'] == True, "Over", "Under")

predictions.sort_index(inplace=True)

# Read in the scores

scores = pd.read_csv("2019_schedule.csv")
predictions["v_score"] = scores["PTS"]
predictions["h_score"] = scores["PTS.1"]

# Determine if I won ATS
predictions["home_cover"] = predictions["h_score"] + predictions["spread"] - predictions["v_score"] > 0
predictions["road_cover"] = predictions["h_score"] + predictions["spread"] - predictions["v_score"] < 0
predictions["spread_push"] = predictions["h_score"] + predictions["spread"] - predictions["v_score"] == 0

predictions.head()

# Read in today's file and determine what day's output I want.

df = pd.read_csv("today.csv")
todays_date = df.iloc[0]['Date']

# Filter for today's games.
today_predictions = predictions[predictions["numeric_date"] == todays_date]
today_predictions = today_predictions.copy()

today_predictions.head()

# Create the actual output for google sheets

# Make a copy and simplify the output
x = today_predictions.copy()
x = x[["Date", "Start (ET)", "Visitor/Neutral", "Home/Neutral", "spread", "odds_total", "xSpread", "spread_delta",
       "pick_home", "xTotal", "total_delta", "pick_over"]]

# Get an absolute value for the spread delta
x["abs_delta"] = x["spread_delta"].abs()

# Get an absolute value for the total delta
x["abs_total_delta"] = x["total_delta"].abs()
x = x.sort_values(by=["abs_delta"], ascending=False)

# Print picks
x['spread_bet'] = np.where(x['pick_home'] == True, x["Home/Neutral"], x["Visitor/Neutral"])
x['total_bet'] = np.where(x['pick_over'] == True, "Over", "Under")
x.to_csv("today_output.csv")
x

# Upload to google docs

os.chdir("C:/Users/kmedvedovsky/Downloads/box/Personal/Python/Projects/NBA/Sheet/Databases")
# use creds to create a client to interact with the Google Drive API
# https://pythonhosted.org/gspread-dataframe/
scope = ['https://spreadsheets.google.com/feeds']
creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
gc = gspread.authorize(creds)
url = "https://docs.google.com/spreadsheets/d/1mhwOLqPu2F9026EQiVxFPIN1t9RGafGpl-dokaIsm9c/edit?usp=sharing"
sheet = gc.open_by_url(url)
worksheet = sheet.get_worksheet(0)

# gd.set_with_dataframe(ws, updated)

# Connecting with `gspread` here

# ws = gc.open("SheetName").worksheet("xyz")
ws = gc.open_by_url(url).get_worksheet(0)

existing = gd.get_as_dataframe(ws)
# updated = existing.append(df, sort=True)
gd.set_with_dataframe(ws, x)
webbrowser.open(url)

# Export the injury report
daily_ratings[["Name", "status", "Inj"]].dropna(thresh=2)