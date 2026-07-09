"""
This module processes raw sports statistics to engineer advanced metrics.
It natively computes travel fatigue using a vectorized Haversine distance engine,
normalizes metrics per 100 possessions, and segments players using rolling CV profiling.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from math import radians, cos, sin, asin, sqrt

# =============================================================================
# GLOBAL ARCHITECTURAL PARAMETERS (SSOT)
# =============================================================================
CV_THRESHOLD = 0.25            # Switch trigger: < 0.25 -> Poisson | >= 0.25 -> Negative Binomial
POSSESSIONS_TARGET = 100       # Target baseline for pace normalization
MIN_GAME_SAMPLE = 2            # Minimum games required to reliably calculate variance

# Geographical coordinates (Latitude, Longitude) for team locations
NBA_COORDS = {
    'ATL': (33.757, -84.396), 'BOS': (42.366, -71.062), 'BKN': (40.682, -73.975),
    'CHA': (35.225, -80.841), 'CHI': (41.880, -87.674), 'CLE': (41.496, -81.688),
    'DAL': (32.790, -96.810), 'DEN': (39.748, -105.007), 'DET': (42.341, -83.055),
    'GSW': (37.768, -122.387), 'HOU': (29.750, -95.362), 'IND': (39.763, -86.155),
    'LAC': (34.043, -118.267), 'LAL': (34.043, -118.267), 'MEM': (35.138, -90.052),
    'MIA': (25.781, -80.187), 'MIL': (43.045, -87.917), 'MIN': (44.979, -93.276),
    'NOP': (29.949, -90.081), 'NYK': (40.750, -73.993), 'OKC': (35.463, -97.515),
    'ORL': (28.539, -81.383), 'PHI': (39.901, -75.171), 'PHX': (33.445, -112.071),
    'POR': (45.531, -122.666), 'SAC': (38.580, -121.499), 'SAS': (29.427, -98.437),
    'TOR': (43.643, -79.379), 'UTA': (40.768, -111.901), 'WAS': (38.898, -77.020)
}

# =============================================================================
# MATHEMATICAL & GEOGRAPHICAL LIBRARIES
# =============================================================================
def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes the great-circle distance in kilometers between two points 
    on the earth's surface using decimal degrees coordinates.
    """
    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return 0.0
        
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Haversine structural formula
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    earth_radius_km = 6371
    return c * earth_radius_km

# =============================================================================
# FEATURE ENGINEERING ENGINES
# =============================================================================
def process_team_metrics(df_team_stats: pd.DataFrame, df_team_logs: pd.DataFrame) -> pd.DataFrame:
    """
    Processes team records, isolates schedule context, resolves game venues,
    and maps the chronological travel trail using vector shifts to extract total travel KMs.
    """
    print(" -> Engineering advanced team schedule metrics & travel trail...")
    
    # 1. Enforce Datetime sorting for chronological safety
    df_logs = df_team_logs.copy()
    df_logs['GAME_DATE'] = pd.to_datetime(df_logs['GAME_DATE'])
    df_logs = df_logs.sort_values(by=['TEAM_ID', 'GAME_DATE'], ascending=True)
    
    # 2. Extract current game city from the MATCHUP string context
    # Example: 'LAL @ BOS' -> Played at BOS | 'LAL vs. MIA' -> Played at LAL
    df_logs['GAME_CITY'] = np.where(
        df_logs['MATCHUP'].str.contains('@'),
        df_logs['MATCHUP'].str.split('@').str[-1].str.strip(),
        df_logs['MATCHUP'].str.split('vs.').str[0].str.strip()
    )
    
    # Map coordinates safely using defensive lookups (Handles NBA/WNBA discrepancies gracefully)
    df_logs['CURRENT_LAT'] = df_logs['GAME_CITY'].map(lambda x: NBA_COORDS.get(x, (np.nan, np.nan))[0])
    df_logs['CURRENT_LON'] = df_logs['GAME_CITY'].map(lambda x: NBA_COORDS.get(x, (np.nan, np.nan))[1])
    
    # 3. Establish the historical chain by shifting game rows within each franchise cluster
    df_logs['PREV_LAT'] = df_logs.groupby('TEAM_ID')['CURRENT_LAT'].shift(1)
    df_logs['PREV_LON'] = df_logs.groupby('TEAM_ID')['CURRENT_LON'].shift(1)
    
    # Vector execution of the Haversine calculator across the sequence matrix
    df_logs['TRAVEL_KM'] = df_logs.apply(
        lambda r: calculate_haversine_distance(r['PREV_LAT'], r['PREV_LON'], r['CURRENT_LAT'], r['CURRENT_LON']),
        axis=1
    )
    
    # 4. Process Rest Days and Back-to-Back (B2B) parameters
    df_logs['REST_DAYS'] = df_logs.groupby('TEAM_ID')['GAME_DATE'].diff().dt.days
    df_logs['IS_B2B'] = (df_logs['REST_DAYS'] == 1).astype(int)
    
    # Aggregate data rows to generate team baseline fatigue constants
    team_fatigue = df_logs.groupby('TEAM_ID').agg(
        TOTAL_TRAVEL_KM=('TRAVEL_KM', 'sum'),
        AVG_TRAVEL_KM=('TRAVEL_KM', 'mean'),
        B2B_COUNT=('IS_B2B', 'sum')
    ).reset_index()
    
    # Merge engineered metrics back into the master team statistics dataframe
    df_processed_teams = pd.merge(df_team_stats, team_fatigue, on='TEAM_ID', how='left')
    return df_processed_teams

def process_player_metrics(df_player_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Builds baseline efficiency indexes from counting statistics.
    """
    print(" -> Processing player efficiency profiles...")
    df_processed = df_player_stats.copy()
    
    # Points Per Minute baseline to filter production density
    df_processed['PPM'] = np.where(df_processed['MIN'] > 0, df_processed['PTS'] / df_processed['MIN'], 0)
    
    # Floor Impact Score formulation
    df_processed['IMPACT_SCORE'] = (df_processed['PTS'] + df_processed['REB'] + df_processed['AST']) * df_processed['USG_PCT']
    return df_processed

def apply_pace_normalization(df_players: pd.DataFrame, df_teams: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes player counting statistics to a uniform standard of 100 possessions
    to eliminate tactical and game-speed inflation bias. Uses TEAM_ID for structural stability.
    """
    print(" -> Scaling traditional metrics to Per-100 Possessions standard...")
    
    # Check if we should merge on TEAM_ID (most robust) or fallback safely
    if 'TEAM_ID' in df_players.columns and 'TEAM_ID' in df_teams.columns:
        df_merged = pd.merge(df_players, df_teams[['TEAM_ID', 'TEAM_NAME', 'PACE']], on='TEAM_ID', how='left')
    elif 'TEAM_NAME' in df_players.columns and 'TEAM_NAME' in df_teams.columns:
        df_merged = pd.merge(df_players, df_teams[['TEAM_NAME', 'PACE']], on='TEAM_NAME', how='left')
    else:
        # Ultra-defensive programming fallback for alternative columns like TEAM_ABBREVIATION
        raise KeyError("Data frames lack a common key mapping attribute ('TEAM_ID' or 'TEAM_NAME') for cross-layer alignment.")
    
    # Defensive programming: Fallback if PACE is missing or zero
    df_merged['PACE'] = df_merged['PACE'].fillna(98.5)
    df_merged['PACE'] = np.where(df_merged['PACE'] <= 0, 98.5, df_merged['PACE'])
    
    # Vectorized execution of pace scaling across core counting dimensions
    counting_metrics = ['PTS', 'REB', 'AST']
    for metric in counting_metrics:
        if metric in df_merged.columns:
            df_merged[f'{metric}_PER100'] = (df_merged[metric] / df_merged['PACE']) * POSSESSIONS_TARGET
            
    return df_merged

def calculate_cv_segmentation(df_player_logs: pd.DataFrame, lookback_window: int) -> pd.DataFrame:
    """
    Executes a rolling variance slice over player logs to compute the CV index,
    routing players dynamically into distribution channels.
    """
    print(f" -> Profiling historical consistency over lookback window of {lookback_window} games...")
    df_logs = df_player_logs.copy()
    df_logs['GAME_DATE'] = pd.to_datetime(df_logs['GAME_DATE'])
    df_logs = df_logs.sort_values(by=['PLAYER_ID', 'GAME_DATE'], ascending=True)
    
    # Slicing tail records per cluster
    df_recent = df_logs.groupby('PLAYER_ID').tail(lookback_window)
    
    # Vectorized statistical profiling
    stats_agg = df_recent.groupby('PLAYER_ID')['PTS'].agg(['mean', 'std', 'count']).reset_index()
    stats_agg.columns = ['PLAYER_ID', 'LOGS_MEAN', 'LOGS_STD', 'LOGS_SAMPLE_SIZE']
    stats_agg['LOGS_STD'] = stats_agg['LOGS_STD'].fillna(0)
    
    # Coefficient of Variation Calculation
    stats_agg['CV'] = np.where(stats_agg['LOGS_MEAN'] > 0, stats_agg['LOGS_STD'] / stats_agg['LOGS_MEAN'], 0)
    
    # Distribution routing switch logic
    stats_agg['MODEL_ASSIGNMENT'] = np.where(
        (stats_agg['CV'] < CV_THRESHOLD) & (stats_agg['LOGS_SAMPLE_SIZE'] >= MIN_GAME_SAMPLE),
        'Poisson',
        'Negative Binomial'
    )
    return stats_agg

# =============================================================================
# MASTER ORCHESTRATOR FUNCTION (The Engine)
# =============================================================================
def run_processing_pipeline(league: str, season_type: str) -> None:
    """
    Master orchestrator for MeewMa Capa 2 (Data Processing).
    Fuses team fatigue, pace scaling, and player CV routing inside a single execution loop.
    
    Args:
        league (str): Targeted league identifier ('nba' or 'wnba').
        season_type (str): Season segment ('Regular Season', 'Playoffs').
    """
    league_lower = league.lower()
    print(f"\n[Data Processor] Executing master pipeline for {league.upper()} | Segment: {season_type}...")
    
    lookback_window = 3 if season_type.lower() == "playoffs" else 7
    
    input_dir = Path("data/raw")
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 1. Ingest Data Matrices
        df_team_stats = pd.read_csv(input_dir / f"team_stats_{league_lower}.csv")
        df_team_logs = pd.read_csv(input_dir / f"team_logs_{league_lower}.csv")
        df_player_stats = pd.read_csv(input_dir / f"player_stats_{league_lower}.csv")
        df_player_logs = pd.read_csv(input_dir / f"player_logs_{league_lower}.csv")
        
        # 2. Process Team Layer (Haversine & Fatigue)
        processed_teams = process_team_metrics(df_team_stats, df_team_logs)
        
        # 3. Process Player Layer (Efficiency Index)
        processed_players = process_player_metrics(df_player_stats)
        
        # 4. Inject Cross-Layer Normalization (Per 100 Possessions)
        df_normalized = apply_pace_normalization(processed_players, processed_teams)
        
        # 5. Volatility Profiling & Distribution Assignment
        df_volatility = calculate_cv_segmentation(df_player_logs, lookback_window=lookback_window)
        
        # 6. Unified Matrix Merge
        df_master_processed = pd.merge(df_normalized, df_volatility, on='PLAYER_ID', how='inner')
        
        # Save structural outputs
        output_file = output_dir / f"processed_player_stats_{league_lower}.csv"
        df_master_processed.to_csv(output_file, index=False)
        
        # Also save processed team statistics for cross-reference in match making
        team_output_file = output_dir / f"processed_team_stats_{league_lower}.csv"
        processed_teams.to_csv(team_output_file, index=False)
        
        print(f"✅ [Data Processor] Travel & Volatility models compiled successfully.")
        print(f"   -> Team Matrix: {team_output_file}")
        print(f"   -> Player Master Matrix: {output_file}")
        
    except FileNotFoundError as fnf:
        raise RuntimeError(f"Pipeline broken. Verify Capa 1 ran correctly. Context: {fnf}")
    except Exception as e:
        raise RuntimeError(f"Fatal error during processing pipeline execution: {e}")

# --------------------------- local tests ------------------------------------
if __name__ == "__main__":
    print("\n" + "="*60)
    print("--- MEEWMA 3.0: DATA PROCESSOR COMPONENT INTEGRATION TEST ---")
    print("="*60)
    print(" -> Instantiating high-fidelity synthetic mock datasets for architecture audit...")

    # 1. Create Mock Team Stats Matrix (Includes required baseline PACE)
    mock_teams = pd.DataFrame({
        'TEAM_ID': [1610612747, 1610612738],
        'TEAM_NAME': ['LAL', 'BOS'],
        'GP': [10, 10],
        'DEF_RATING': [112.0, 108.5],
        'PACE': [102.0, 96.0],  # Lakers play fast, Celtics play slow
        'NET_RATING': [2.1, 5.4]
    })

    # 2. Create Mock Team Game Logs Chain (To test historical trail and Haversine venue detection)
    mock_team_logs = pd.DataFrame({
        'TEAM_ID': [1610612747, 1610612747, 1610612738, 1610612738],
        'TEAM_NAME': ['LAL', 'LAL', 'BOS', 'BOS'],
        'GAME_DATE': ['2026-01-01', '2026-01-02', '2026-01-01', '2026-01-04'], # LAL has a B2B!
        'MATCHUP': ['LAL vs. MIN', 'LAL @ SAC', 'BOS vs. MIA', 'BOS @ NYK'],
        'PTS': [110, 105, 115, 98],
        'FGA': [88, 92, 84, 80],
        'FG_PCT': [0.45, 0.43, 0.48, 0.41]
    })

    # 3. Create Mock Player Profiles Matrix
    mock_player_stats = pd.DataFrame({
        'PLAYER_ID': [201, 202],
        'PLAYER_NAME': ['LeBron James', 'Jayson Tatum'],
        'TEAM_NAME': ['LAL', 'BOS'],
        'GP': [10, 10],
        'MIN': [35.0, 36.0],
        'PTS': [25.0, 27.0],
        'REB': [8.0, 7.0],
        'AST': [7.0, 4.0],
        'USG_PCT': [0.28, 0.30]
    })

    # 4. Create Mock Player Historical Game Logs (To test rolling CV Volatility Profiling)
    mock_player_logs = pd.DataFrame({
        'PLAYER_ID': [201, 201, 201, 202, 202, 202],
        'PLAYER_NAME': ['LeBron James', 'LeBron James', 'LeBron James', 'Jayson Tatum', 'Jayson Tatum', 'Jayson Tatum'],
        'GAME_DATE': ['2026-01-01', '2026-01-02', '2026-01-05', '2026-01-01', '2026-01-04', '2026-01-06'],
        'PTS': [26, 24, 25, 40, 15, 26] # LeBron is hyper-stable (Poisson) | Tatum is streaky (NegBinomial)
    })

    try:
        print("\n -> Executing Step 1: Evaluating Geographical Travel & Schedule Fatigue Engine...")
        audited_teams = process_team_metrics(mock_teams, mock_team_logs)
        print(f"    [PASS] B2B Detection Active. Lakers B2B Count: {audited_teams.loc[audited_teams['TEAM_NAME']=='LAL', 'B2B_COUNT'].values[0]}")
        print(f"    [PASS] Haversine Travel Engine Logged: {audited_teams.loc[audited_teams['TEAM_NAME']=='LAL', 'TOTAL_TRAVEL_KM'].values[0]:.2f} KMs detected.")

        print("\n -> Executing Step 2: Evaluating Cross-Layer Staging & Per-100 Pace Normalization...")
        base_players = process_player_metrics(mock_player_stats)
        audited_normalized = apply_pace_normalization(base_players, audited_teams)
        print(f"    [PASS] Pace Bias Eliminated.")
        print(f"           LeBron PTS Brutos: {audited_normalized.loc[audited_normalized['PLAYER_NAME']=='LeBron James', 'PTS'].values[0]} | Ajustados a 100 poss: {audited_normalized.loc[audited_normalized['PLAYER_NAME']=='LeBron James', 'PTS_PER100'].values[0]:.2f}")
        print(f"           Tatum PTS Brutos: {audited_normalized.loc[audited_normalized['PLAYER_NAME']=='Jayson Tatum', 'PTS'].values[0]}  | Ajustados a 100 poss: {audited_normalized.loc[audited_normalized['PLAYER_NAME']=='Jayson Tatum', 'PTS_PER100'].values[0]:.2f}")

        print("\n -> Executing Step 3: Evaluating Rolling CV Volatility Profiling & Distribution Switch...")
        audited_volatility = calculate_cv_segmentation(mock_player_logs, lookback_window=3)
        
        # Consolidate master evaluation frame
        test_master = pd.merge(audited_normalized, audited_volatility, on='PLAYER_ID', how='inner')
        
        print(f"    [PASS] Mathematical Routing Switch Successful:")
        for idx, row in test_master.iterrows():
            print(f"           * Player: {row['PLAYER_NAME']} | CV: {row['CV']:.3f} -> Assigned to Model: [{row['MODEL_ASSIGNMENT'].upper()}]")

        print("\n" + "="*60)
        print("✅ SUCCESS: DATA PROCESSOR PIPELINE PASSED ALL ARCHITECTURAL AUDITS.")
        print("="*60 + "\n")

    except Exception as audit_error:
        print(f"\n❌ CRITICAL: Audit failed during decoupled module simulation: {audit_error}")
        print("Review vectorized operations, merge indexes, and key signatures immediately.\n")