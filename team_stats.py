from statsbombpy import sb
import pandas as pd
import numpy as np

matches = sb.matches(competition_id=43, season_id=106)
match_ids = matches['match_id'].tolist()

all_events = []
for match_id in match_ids:
    events = sb.events(match_id=match_id)
    events['match_id'] = match_id
    all_events.append(events)

all_events_df = pd.concat(all_events, ignore_index=True)
all_events_df.to_csv('wc2022_all_events_teams.csv', index=False)
print(f"Total events collected: {len(all_events_df)}")
print("Saved!")