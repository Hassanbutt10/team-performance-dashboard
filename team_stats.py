from statsbombpy import sb
import pandas as pd
import numpy as np

# Load saved event data (no need to re-pull from StatsBomb)
events = pd.read_csv('wc2022_all_events_teams.csv', low_memory=False)

# Small call, fast, gets match list with home/away teams
matches = sb.matches(competition_id=43, season_id=106)

# Goals and xG: use shot events, exclude penalty shootout
shots = events[events['type'] == 'Shot'].copy()
shots = shots[shots['shot_type'] != 'Penalty']
shots['is_goal'] = (shots['shot_outcome'] == 'Goal').astype(int)

goals_for = shots.groupby('team')['is_goal'].sum().reset_index(name='goals_for')
xg_for = shots.groupby('team')['shot_statsbomb_xg'].sum().reset_index(name='xg_for')
shots_per_team = shots.groupby('team').size().reset_index(name='total_shots')

# Games played per team
home_teams = matches[['match_id', 'home_team']].rename(columns={'home_team': 'team'})
away_teams = matches[['match_id', 'away_team']].rename(columns={'away_team': 'team'})
all_team_matches = pd.concat([home_teams, away_teams])
games_played = all_team_matches.groupby('team').size().reset_index(name='games_played')

# Merge into one team stats table
team_stats = goals_for.merge(xg_for, on='team')
team_stats = team_stats.merge(shots_per_team, on='team')
team_stats = team_stats.merge(games_played, on='team')

team_stats['goals_per_game'] = team_stats['goals_for'] / team_stats['games_played']
team_stats['xg_per_game'] = team_stats['xg_for'] / team_stats['games_played']
team_stats['shots_per_game'] = team_stats['total_shots'] / team_stats['games_played']

team_stats = team_stats.sort_values('xg_per_game', ascending=False)
print(team_stats.head(15))

team_stats.to_csv('team_stats.csv', index=False)
print("Saved team_stats.csv")