from statsbombpy import sb
import pandas as pd
import numpy as np

events = pd.read_csv('wc2022_all_events_teams.csv', low_memory=False)
matches = sb.matches(competition_id=43, season_id=106)

# Goals and xG
shots = events[events['type'] == 'Shot'].copy()
shots = shots[shots['shot_type'] != 'Penalty']
shots['is_goal'] = (shots['shot_outcome'] == 'Goal').astype(int)

goals_for = shots.groupby('team')['is_goal'].sum().reset_index(name='goals_for')
xg_for = shots.groupby('team')['shot_statsbomb_xg'].sum().reset_index(name='xg_for')
shots_per_team = shots.groupby('team').size().reset_index(name='total_shots')

home_teams = matches[['match_id', 'home_team']].rename(columns={'home_team': 'team'})
away_teams = matches[['match_id', 'away_team']].rename(columns={'away_team': 'team'})
all_team_matches = pd.concat([home_teams, away_teams])
games_played = all_team_matches.groupby('team').size().reset_index(name='games_played')

# Possession %: proxy using share of total passes attempted per match
passes = events[events['type'] == 'Pass'].copy()
passes_per_team_match = passes.groupby(['match_id', 'team']).size().reset_index(name='pass_count')
total_passes_per_match = passes_per_team_match.groupby('match_id')['pass_count'].sum().reset_index(name='total_match_passes')
passes_per_team_match = passes_per_team_match.merge(total_passes_per_match, on='match_id')
passes_per_team_match['possession_pct'] = (passes_per_team_match['pass_count'] / passes_per_team_match['total_match_passes']) * 100
possession_by_team = passes_per_team_match.groupby('team')['possession_pct'].mean().reset_index()

# PPDA: opponent's passes in their own defensive third, divided by this team's defensive actions in their attacking third
# StatsBomb coordinates: each team's own events are oriented toward x=120 as their attacking direction
passes['location'] = passes['location'].apply(eval)
passes['x'] = passes['location'].apply(lambda loc: loc[0])
opponent_def_third_passes = passes[passes['x'] < 40]

defensive_events = events[events['type'].isin(['Pressure', 'Duel', 'Interception', 'Foul Committed'])].copy()
defensive_events['location'] = defensive_events['location'].apply(lambda v: eval(v) if pd.notna(v) else None)
defensive_events = defensive_events.dropna(subset=['location'])
defensive_events['x'] = defensive_events['location'].apply(lambda loc: loc[0])
attacking_third_actions = defensive_events[defensive_events['x'] > 80]

# Match up: for each match, each team's PPDA uses the OPPONENT's defensive third passes
# Build a match+team to opponent mapping
match_teams = matches[['match_id', 'home_team', 'away_team']]

def get_opponent(row, match_teams):
    m = match_teams[match_teams['match_id'] == row['match_id']]
    if len(m) == 0:
        return None
    if row['team'] == m.iloc[0]['home_team']:
        return m.iloc[0]['away_team']
    else:
        return m.iloc[0]['home_team']

opp_passes_by_match = opponent_def_third_passes.groupby(['match_id', 'team']).size().reset_index(name='opp_def_passes')
opp_passes_by_match['pressing_team'] = opp_passes_by_match.apply(lambda r: get_opponent(r, match_teams), axis=1)

def_actions_by_match = attacking_third_actions.groupby(['match_id', 'team']).size().reset_index(name='def_actions')

ppda_merge = opp_passes_by_match.merge(def_actions_by_match, left_on=['match_id', 'pressing_team'], right_on=['match_id', 'team'], suffixes=('_opp', '_press'))
ppda_by_team = ppda_merge.groupby('pressing_team').agg({'opp_def_passes': 'sum', 'def_actions': 'sum'}).reset_index()
ppda_by_team['ppda'] = ppda_by_team['opp_def_passes'] / ppda_by_team['def_actions']
ppda_by_team = ppda_by_team.rename(columns={'pressing_team': 'team'})

# Merge everything
team_stats = goals_for.merge(xg_for, on='team')
team_stats = team_stats.merge(shots_per_team, on='team')
team_stats = team_stats.merge(games_played, on='team')
team_stats = team_stats.merge(possession_by_team, on='team')
team_stats = team_stats.merge(ppda_by_team[['team', 'ppda']], on='team')

team_stats['goals_per_game'] = team_stats['goals_for'] / team_stats['games_played']
team_stats['xg_per_game'] = team_stats['xg_for'] / team_stats['games_played']
team_stats['shots_per_game'] = team_stats['total_shots'] / team_stats['games_played']

team_stats = team_stats.sort_values('xg_per_game', ascending=False)
print(team_stats[['team', 'goals_per_game', 'xg_per_game', 'shots_per_game', 'possession_pct', 'ppda']].head(15))

team_stats.to_csv('team_stats.csv', index=False)
print("Saved team_stats.csv")