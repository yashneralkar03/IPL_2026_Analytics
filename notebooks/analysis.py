import pandas as pd
import json
import os

# ── 1. Load all JSON match files ──────────────────────────
data_folder = 'data'
all_deliveries = []

for filename in os.listdir(data_folder):
    if filename.endswith('.json'):
        filepath = os.path.join(data_folder, filename)
        
        with open(filepath, 'r') as f:
            match = json.load(f)
        
        # Extract match info
        match_id = filename.replace('.json', '')
        info = match.get('info', {})
        season = info.get('season', 'Unknown')
        venue = info.get('venue', 'Unknown')
        teams = info.get('teams', [])

        # Extract ball by ball data
        innings = match.get('innings', [])
        
        for inning_idx, inning in enumerate(innings):
            batting_team = inning.get('team', '')
            overs = inning.get('overs', [])
            
            for over_data in overs:
                over_num = over_data.get('over', 0) + 1  # make it 1-indexed
                deliveries = over_data.get('deliveries', [])
                
                for delivery in deliveries:
                    batter = delivery.get('batter', '')
                    bowler = delivery.get('bowler', '')
                    runs = delivery.get('runs', {})
                    batter_runs = runs.get('batter', 0)
                    extras = runs.get('extras', 0)
                    extra_type = list(delivery.get('extras', {}).keys())
                    is_wide = 'wides' in extra_type
                    
                    wickets = delivery.get('wickets', [])
                    player_dismissed = wickets[0].get('player_out', None) if wickets else None

                    all_deliveries.append({
                        'match_id': match_id,
                        'season': season,
                        'venue': venue,
                        'batting_team': batting_team,
                        'inning': inning_idx + 1,
                        'over': over_num,
                        'batter': batter,
                        'bowler': bowler,
                        'batsman_runs': batter_runs,
                        'wide_runs': 1 if is_wide else 0,
                        'player_dismissed': player_dismissed
                    })

# ── 2. Convert to dataframe ───────────────────────────────
df = pd.DataFrame(all_deliveries)

print(f"Total deliveries loaded: {len(df)}")
print(df.columns.tolist())
print(df.head(3))

# ── 3. Filter out wides ───────────────────────────────────
df_batting = df[df['wide_runs'] == 0].copy()


# ── 4. Create Phase column ────────────────────────────────
def get_phase(over):
    if over <= 6:
        return 'Powerplay'
    elif over <= 15:        
        return 'Middle'    
    else:
        return 'Death'
    
df_batting['phase'] = df_batting['over'].apply(get_phase) 
#
##
# #── 5. Aggregate batter stats by phase ───────────────────
#phase_stats = df_batting.groupby(['batter', 'phase']).agg(
#    runs       = ('batsman_runs', 'sum'),
#    balls      = ('batsman_runs', 'count'),
#    dismissals = ('player_dismissed', lambda x: x.notna().sum())
#).reset_index()

#phase_stats['strike_rate'] = (phase_stats['runs'] / phase_stats['balls'] * 100).round(2)
#phase_stats['avg'] = (phase_stats['runs'] / phase_stats['dismissals'].replace(0, 1)).round(2)

# ── 6. Filter min 100 balls ───────────────────────────────
#phase_stats_filtered = phase_stats[phase_stats['balls'] >= 100]

# ── 7. Export for Power BI ────────────────────────────────
#phase_stats_filtered.to_csv('output/clean_data.csv', index=False)
#print("✅ clean_data.csv exported — ready for Power BI")

# Filter to 2026 season
df_2026 = df[df['season'] == '2026'].copy()

print(f"Total deliveries in 2026: {len(df_2026)}")
print(f"Total matches in 2026: {df_2026['match_id'].nunique()}")

# Filter out wides
df_2026_batting = df_2026[df_2026['wide_runs'] == 0].copy()

# Add phase column
df_2026_batting['phase'] = df_2026_batting['over'].apply(get_phase)

# Aggregate batter stats — lower threshold (30 balls) for single season
phase_stats_2026 = df_2026_batting.groupby(['batter', 'phase']).agg(
    runs       = ('batsman_runs', 'sum'),
    balls      = ('batsman_runs', 'count'),
    dismissals = ('player_dismissed', lambda x: x.notna().sum())
).reset_index()

phase_stats_2026['strike_rate'] = (phase_stats_2026['runs'] / phase_stats_2026['balls'] * 100).round(2)
phase_stats_2026['avg'] = (phase_stats_2026['runs'] / phase_stats_2026['dismissals'].replace(0, 1)).round(2)

# Lower threshold for single season
phase_stats_2026_filtered = phase_stats_2026[phase_stats_2026['balls'] >= 30]

print(f"\nUnique batters with 30+ balls in 2026: {phase_stats_2026_filtered['batter'].nunique()}")


# ── 3. Pace vs Spin Analysis ──────────────────────────────
# Classify bowlers as pace or spin based on common name patterns
spin_keywords = ['aj hosein', 'ak markram', 'am ghazanfar', 'ar patel', 'as roy', 
                'abdul samad', 'abhishek sharma', 'cv varun', 'ds rathi', 'gf linde',
                'harsh dubey', 'kh pandya', 'kuldeep yadav', 'm markande', 'm siddharth',
                'mj santner', 'mw short', 'noor ahmad', 'r parag', 'ra jadeja', 'rd chahar',
                'rashid khan', 'ravi bishnoi', 'sp narine', 'shahbaz ahmed', 'shivang kumar',
                'suyash sharma', 'th david', 'v nigam', 'washington sundar', 'ys chahal']

def bowler_type(name):
    name_lower = name.lower()
    if any(keyword in name_lower for keyword in spin_keywords):
        return 'Spin'
    return 'Pace'

df_2026_batting['bowler_type'] = df_2026_batting['bowler'].apply(bowler_type)

pace_spin = df_2026_batting.groupby(['batter', 'bowler_type']).agg(
    runs  = ('batsman_runs', 'sum'),
    balls = ('batsman_runs', 'count')
).reset_index()

pace_spin['strike_rate'] = (pace_spin['runs'] / pace_spin['balls'] * 100).round(2)
pace_spin_2026_filtered = pace_spin[pace_spin['balls'] >= 20]
# Top 10 batters vs spin
top_vs_spin = pace_spin_2026_filtered[pace_spin_2026_filtered['bowler_type'] == 'Spin']
top_vs_spin = top_vs_spin.sort_values('strike_rate', ascending=False).head(10)
print("\n🔄 Top 10 Batters vs Spin in IPL 2026:")
print(top_vs_spin[['batter', 'runs', 'balls', 'strike_rate']])


# Top 10 death over batters in 2026
death_2026 = phase_stats_2026_filtered[phase_stats_2026_filtered['phase'] == 'Death']
top_death_2026 = death_2026.sort_values('strike_rate', ascending=False).head(10)
print("\n🏏 Top Death Over Batters IPL 2026:")
print(top_death_2026[['batter', 'runs', 'balls', 'strike_rate']])

# Top 10 powerplay batters in 2026
pp_2026 = phase_stats_2026_filtered[phase_stats_2026_filtered['phase'] == 'Powerplay']
top_pp_2026 = pp_2026.sort_values('strike_rate', ascending=False).head(10)
print("\n🏏 Top Powerplay Batters IPL 2026:")
print(top_pp_2026[['batter', 'runs', 'balls', 'strike_rate']])

# Top 10 middle overs batters in 2026
middle_2026 = phase_stats_2026_filtered[phase_stats_2026_filtered['phase'] == 'Middle']
top_middle_2026 = middle_2026.sort_values('strike_rate', ascending=False).head(10)
print("\n🏏 Top Middle Overs Batters IPL 2026:")
print(top_middle_2026[['batter', 'runs', 'balls', 'strike_rate']])

# Pace vs spin in 2026
df_2026_batting['bowler_type'] = df_2026_batting['bowler'].apply(bowler_type)

pace_spin_2026 = df_2026_batting.groupby(['batter', 'bowler_type']).agg(
    runs  = ('batsman_runs', 'sum'),
    balls = ('batsman_runs', 'count')
).reset_index()

pace_spin_2026['strike_rate'] = (pace_spin_2026['runs'] / pace_spin_2026['balls'] * 100).round(2)
# Find batters who qualify against at least one bowler type (20+ balls)
qualifying_pace_spin = pace_spin_2026[pace_spin_2026['balls'] >= 20]['batter'].unique()

# Keep all bowler type rows for those batters
pace_spin_2026_filtered = pace_spin_2026[pace_spin_2026['batter'].isin(qualifying_pace_spin)]

top_vs_spin_2026 = pace_spin_2026_filtered[pace_spin_2026_filtered['bowler_type'] == 'Spin']
top_vs_spin_2026 = top_vs_spin_2026.sort_values('strike_rate', ascending=False).head(10)
print("\n🔄 Top Batters vs Spin in IPL 2026:")
print(top_vs_spin_2026[['batter', 'runs', 'balls', 'strike_rate']])


phase_stats_2026_filtered.to_csv('output/clean_data_2026.csv', index=False)
top_death_2026.to_csv('output/death_sr_2026.csv', index=False)
top_pp_2026.to_csv('output/powerplay_sr_2026.csv', index=False)
top_middle_2026.to_csv('output/middle_sr_2026.csv', index=False)
pace_spin_2026_filtered.to_csv('output/pace_vs_spin_2026.csv', index=False)

print("\n✅ All 2026 CSVs exported — ready for Power BI")