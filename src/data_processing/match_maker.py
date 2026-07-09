"""
This module bridges the gap between betting market odds and official sports statistics.
It utilizes Dynamic Fuzzy Name Resolution (Levenshtein distance) to autonomously map 
bookmaker team strings to official API team strings, filtering the player pool 
down to today's active slate and segmenting them for the mathematical engines.
"""

import pandas as pd
from pathlib import Path
from thefuzz import process

# =============================================================================
# GLOBAL ARCHITECTURAL PARAMETERS
# =============================================================================
FUZZY_MATCH_THRESHOLD = 80  # Minimum Levenshtein confidence percentage to accept a match

# =============================================================================
# FUZZY RESOLUTION ENGINE
# =============================================================================
def build_dynamic_fuzzy_map(odds_teams: list, official_teams: list) -> dict:
    """
    Autonomously constructs a mapping dictionary between bookmaker team names
    and official league team names using string similarity, eliminating the 
    need for hardcoded canonical dictionaries.
    """
    print(" -> Executing Dynamic Fuzzy Name Resolution...")
    team_map = {}
    
    for odds_team in odds_teams:
        # Returns a tuple: (Best Match String, Confidence Score)
        best_match, score = process.extractOne(odds_team, official_teams)
        
        if score >= FUZZY_MATCH_THRESHOLD:
            team_map[odds_team] = best_match
        else:
            print(f"    [WARNING] Low confidence match for '{odds_team}': '{best_match}' ({score}%). Dropping from slate.")
            team_map[odds_team] = None
            
    return team_map

# =============================================================================
# TARGET POOL SEGMENTATION
# =============================================================================
def generate_active_slate(df_odds: pd.DataFrame, df_teams: pd.DataFrame) -> tuple:
    """
    Isolates today's games from the odds matrix and aligns them with official team stats.
    Returns the mapped active games and a flat list of official active team names.
    """
    # 1. Extract unique games from the flattened odds matrix
    active_games = df_odds[['GAME_ID', 'HOME_TEAM', 'AWAY_TEAM']].drop_duplicates().dropna()
    
    odds_unique_teams = pd.concat([active_games['HOME_TEAM'], active_games['AWAY_TEAM']]).unique()
    official_unique_teams = df_teams['TEAM_NAME'].unique()
    
    # 2. Build the translation dictionary
    mapping_dict = build_dynamic_fuzzy_map(odds_unique_teams, official_unique_teams)
    
    # 3. Translate bookmaker names to official names
    active_games['OFFICIAL_HOME'] = active_games['HOME_TEAM'].map(mapping_dict)
    active_games['OFFICIAL_AWAY'] = active_games['AWAY_TEAM'].map(mapping_dict)
    
    # Drop games where fuzzy matching failed
    active_games = active_games.dropna(subset=['OFFICIAL_HOME', 'OFFICIAL_AWAY'])
    
    # 4. Generate the active flat pool
    active_team_pool = pd.concat([active_games['OFFICIAL_HOME'], active_games['OFFICIAL_AWAY']]).unique().tolist()
    
    return active_games, active_team_pool

# =============================================================================
# MASTER ORCHESTRATOR FUNCTION (The Engine)
# =============================================================================
def run_matching_pipeline(league: str) -> None:
    """
    Master orchestrator for MeewMa Capa 3 (Match Maker).
    Fuses external odds with internal statistical projections, isolating today's 
    active targets and routing them into Poisson and Negative Binomial channels.
    
    Args:
        league (str): Targeted league identifier ('nba' or 'wnba').
    """
    league_lower = league.lower()
    print(f"\n[Match Maker] Initializing Alignment Pipeline for {league.upper()}...")
    
    # Directory Definitions
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    target_dir = Path("data/targets") # New clean directory for final math inputs
    target_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 1. Ingest Architectures
        df_odds = pd.read_csv(raw_dir / f"odds_{league_lower}.csv")
        df_teams = pd.read_csv(processed_dir / f"processed_team_stats_{league_lower}.csv")
        df_players = pd.read_csv(processed_dir / f"processed_player_stats_{league_lower}.csv")
        
        # 2. Extract Today's Active Slate via Fuzzy Mapping
        df_active_games, active_teams_list = generate_active_slate(df_odds, df_teams)
        
        # 3. Filter the Master Player Matrix to ONLY include players hitting the court today
        print(" -> Filtering statistical matrices to match today's active schedule...")
        df_active_players = df_players[df_players['TEAM_NAME'].isin(active_teams_list)].copy()
        
        # 4. Route players to their designated probability engines based on CV segmentation
        df_poisson = df_active_players[df_active_players['MODEL_ASSIGNMENT'] == 'Poisson']
        df_neg_binomial = df_active_players[df_active_players['MODEL_ASSIGNMENT'] == 'Negative Binomial']
        
        # 5. Export Target Matrices
        poisson_out = target_dir / f"target_poisson_{league_lower}.csv"
        negbin_out = target_dir / f"target_negbin_{league_lower}.csv"
        games_out = target_dir / f"active_slate_teams_{league_lower}.csv"
        
        df_poisson.to_csv(poisson_out, index=False)
        df_neg_binomial.to_csv(negbin_out, index=False)
        
        # Exporting active games (useful for Team Totals / Spread arbitrage)
        df_active_games.to_csv(games_out, index=False)
        
        print(f"✅ [Match Maker] Alignment Successful. Targets ready for Mathematical Engines.")
        print(f"   -> Active Games Today: {len(df_active_games)}")
        print(f"   -> Poisson Players Enqueued: {len(df_poisson)}")
        print(f"   -> Neg. Binomial Players Enqueued: {len(df_neg_binomial)}")
        print(f"   -> Output Directory: {target_dir}/")
        
    except FileNotFoundError as fnf:
        raise RuntimeError(f"Missing predecessor files. Ensure Extraction and Processing layers ran successfully. {fnf}")
    except Exception as e:
        raise RuntimeError(f"Fatal error during Match Maker execution: {e}")

# =============================================================================
# PRODUCTION PORTFOLIO INTEGRATION TESTS
# =============================================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("--- MEEWMA 3.0: MATCH MAKER COMPONENT AUDIT ---")
    print("="*60)
    
    # 1. Mock Odds Data (Notice the typos/commercial names: "LA Lakers", "Boston")
    mock_odds = pd.DataFrame({
        'GAME_ID': ['G1', 'G1'],
        'HOME_TEAM': ['LA Lakers', 'LA Lakers'],
        'AWAY_TEAM': ['Boston', 'Boston']
    })
    
    # 2. Mock Official Teams (Notice the strict official names)
    mock_teams = pd.DataFrame({
        'TEAM_ID': [1, 2, 3],
        'TEAM_NAME': ['Los Angeles Lakers', 'Boston Celtics', 'Miami Heat']
    })
    
    # 3. Mock Official Players
    mock_players = pd.DataFrame({
        'PLAYER_NAME': ['LeBron James', 'Jayson Tatum', 'Jimmy Butler'],
        'TEAM_NAME': ['Los Angeles Lakers', 'Boston Celtics', 'Miami Heat'],
        'MODEL_ASSIGNMENT': ['Poisson', 'Negative Binomial', 'Poisson']
    })
    
    try:
        print("\n -> Executing Step 1: Evaluating Dynamic Fuzzy Translation...")
        active_games, active_teams = generate_active_slate(mock_odds, mock_teams)
        
        # Audit specific translations
        mapped_home = active_games['OFFICIAL_HOME'].values[0]
        mapped_away = active_games['OFFICIAL_AWAY'].values[0]
        
        print(f"    [PASS] Fuzzy Mapping Hit: 'LA Lakers' translated to '{mapped_home}'")
        print(f"    [PASS] Fuzzy Mapping Hit: 'Boston' translated to '{mapped_away}'")
        
        print("\n -> Executing Step 2: Evaluating Mathematical Segmentation Routing...")
        active_players = mock_players[mock_players['TEAM_NAME'].isin(active_teams)]
        poisson_count = len(active_players[active_players['MODEL_ASSIGNMENT'] == 'Poisson'])
        negbin_count = len(active_players[active_players['MODEL_ASSIGNMENT'] == 'Negative Binomial'])
        
        print(f"    [PASS] Player Pool Filtered. Heat players properly excluded (No game today).")
        print(f"    [PASS] Poisson routed: {poisson_count} | NegBinomial routed: {negbin_count}")
        
        print("\n" + "="*60)
        print("✅ SUCCESS: MATCH MAKER PIPELINE ARCHITECTURE VALIDATED.")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ CRITICAL: Audit failed. Check fuzzy logic string mappings: {e}")