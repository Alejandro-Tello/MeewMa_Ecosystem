#This module extracts NBA stadistics from nba_api 
# This module extracts NBA/WNBA statistics from nba_api
import os
import pandas as pd
import datetime
from pathlib import Path
from nba_api.stats.endpoints import leaguedashteamstats, leaguedashplayerstats, playergamelogs, teamgamelogs


def get_current_season(league_id: str) -> str:
    """
    Dynamically generates the current season string based on the system date.
    
    Args:
        league_id (str): '00' for NBA, '10' for WNBA.
        
    Returns:
        str: Season formatted for the NBA API (e.g., '2025-26' or '2026').
    """
    today = datetime.datetime.now()
    if league_id == "00":
        # NBA: Year crossover format
        start_year = today.year - 1 if today.month < 10 else today.year
        end_year = str(start_year + 1)[-2:]
        return f"{start_year}-{end_year}"
    else:
        # WNBA: Calendar year format
        return str(today.year)

def get_team_stats(league_id: str, season_type: str) -> pd.DataFrame:
    """
    Extracts advanced team statistics from the API.
    """
    liga = "NBA" if league_id == "00" else "WNBA" if league_id == "10" else "G-League"
    print(f" -> [API Call] Extracting Team Statistics for {liga} ({season_type})...")
    
    team_stats = leaguedashteamstats.LeagueDashTeamStats(
        measure_type_detailed_defense='Advanced',
        season_type_all_star=season_type,
        league_id_nullable=league_id
    )
    
    df_teams = team_stats.get_data_frames()[0]
    columns_to_keep = ['TEAM_ID', 'TEAM_NAME', 'GP', 'DEF_RATING', 'PACE', 'NET_RATING']
    return df_teams[columns_to_keep]

def get_player_stats(league_id: str, season_type: str) -> pd.DataFrame:
    """
    Extracts traditional and advanced player stats and merges them.
    """
    liga = "NBA" if league_id == "00" else "WNBA" if league_id == "10" else "G-League"
    print(f" -> [API Call] Extracting Player Statistics for {liga} ({season_type})...")
    
    player_adv = leaguedashplayerstats.LeagueDashPlayerStats(
        measure_type_detailed_defense='Advanced',
        season_type_all_star=season_type,
        league_id_nullable=league_id
    )
    df_adv = player_adv.get_data_frames()[0]
    
    player_trad = leaguedashplayerstats.LeagueDashPlayerStats(
        measure_type_detailed_defense='Base',
        season_type_all_star=season_type,
        league_id_nullable=league_id
    )
    df_trad = player_trad.get_data_frames()[0]
    
    df_merged = pd.merge(
        df_trad[['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION', 'GP', 'MIN', 'PTS', 'REB', 'AST']],
        df_adv[['PLAYER_ID', 'USG_PCT']],
        on='PLAYER_ID'
    )
    return df_merged

def get_player_game_logs(league_id: str, season_type: str) -> pd.DataFrame:
    """
    Extracts game logs for all players in the league using dynamic season fetching.
    """
    season = get_current_season(league_id)
    liga = "NBA" if league_id == "00" else "WNBA"
    print(f" -> [API Call] Extracting Player Logs for {liga} ({season_type}) - Season: {season}...")
    
    logs = playergamelogs.PlayerGameLogs(
        league_id_nullable=league_id,
        season_type_nullable=season_type,
        season_nullable=season  
    )
    
    df_logs = logs.get_data_frames()[0]
    columns_to_keep = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION', 
                       'GAME_DATE', 'MATCHUP', 'MIN', 'PTS', 'REB', 'AST']
    return df_logs[columns_to_keep]

def get_team_game_logs(league_id: str, season_type: str) -> pd.DataFrame:
    """
    Extracts game logs for all teams in the league. Useful for streaks and Back-to-Back flags.
    """
    season = get_current_season(league_id)
    liga = "NBA" if league_id == "00" else "WNBA"
    print(f" -> [API Call] Extracting Team Logs for {liga} ({season_type}) - Season: {season}...")
    
    logs = teamgamelogs.TeamGameLogs(
        league_id_nullable=league_id,
        season_type_nullable=season_type,
        season_nullable=season
    )
    
    df_logs = logs.get_data_frames()[0]
    columns_to_keep = ['TEAM_ID', 'TEAM_NAME', 'GAME_DATE', 'MATCHUP', 
                       'PTS', 'FGM', 'FGA', 'FG_PCT']
    return df_logs[columns_to_keep]

# =============================================================================
# MASTER ORCHESTRATOR FUNCTION (The Engine)
# =============================================================================
def run_stats_pipeline(league: str, season_type: str) -> None:
    """
    Master orchestrator for the official NBA/WNBA API data extraction.
    Injects the correct league_id and season_type parameters down to all extraction engines.
    
    Args:
        league (str): The targeted league identifier ('nba' or 'wnba').
        season_type (str): The official API season segment ('Regular Season', 'Playoffs', 'Pre Season').
    """
    league_id = "00" if league.lower() == "nba" else "10"
    print(f"\n[NBA API] Starting extraction pipeline for {league.upper()} | Phase: {season_type}...")
    
    try:
        # Sequential Data Extraction passing variables downward via SSOT pattern
        df_team_stats = get_team_stats(league_id=league_id, season_type=season_type)
        df_player_stats = get_player_stats(league_id=league_id, season_type=season_type)
        df_team_logs = get_team_game_logs(league_id=league_id, season_type=season_type)
        df_player_logs = get_player_game_logs(league_id=league_id, season_type=season_type)
        
        # File System Operations
        output_dir = Path("data/raw")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Saving all 4 matrices dynamically using lowercase 'league' to avoid overwrites
        df_team_stats.to_csv(output_dir / f"team_stats_{league.lower()}.csv", index=False)
        df_player_stats.to_csv(output_dir / f"player_stats_{league.lower()}.csv", index=False)
        df_team_logs.to_csv(output_dir / f"team_logs_{league.lower()}.csv", index=False)
        df_player_logs.to_csv(output_dir / f"player_logs_{league.lower()}.csv", index=False)
        
        print(f"✅ [NBA API] Successfully cached 4 data matrices for {league.upper()} into {output_dir}/")
        
    except Exception as e:
        raise RuntimeError(f"Failed to complete stats pipeline for {league.upper()}: {e}")

# --------------------------- local tests ------------------------------------
if __name__ == "__main__":
    print("--- NBA/WNBA Data Local Integration Check ---")
    
    # Simulating standard main.py user inputs
    test_league = "wnba" 
    test_season_type = "Regular Season"
    
    try:
        run_stats_pipeline(league=test_league, season_type=test_season_type)
        print("\n✅ Local pipeline validation completed successfully.")
    except Exception as e:
        print(f"\n❌ Pipeline failed during testing: {e}")