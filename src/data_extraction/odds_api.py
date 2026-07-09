#This module extracts data from sports odds API for desired sport 
"""
This module extracts real-time sports betting odds from The Odds API.
It is designed to be fully integrated into the MeewMa 3.0 ecosystem.
"""

import os
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (e.g., API keys) from a .env file
load_dotenv()

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================
# Make sure ODDS_API_KEY is defined in your environment or .env file
API_KEY = os.getenv("ODDS_API_KEY") 
REGIONS = "us" # 'uk', 'us', 'eu', 'au'. Multiple can be specified if comma delimited
MARKETS = "h2h,spreads,totals" # 'h2h' (moneyline), 'spreads', 'totals'
ODDS_FORMAT = "decimal" # 'decimal', 'american'
DATE_FORMAT = "iso" # 'iso', 'unix'

def get_sport_key(league: str) -> str:
    """
    Maps the generic league name to The Odds API specific sport key.
    
    Args:
        league (str): The targeted league identifier ('nba' or 'wnba').
        
    Returns:
        str: The official sport key used by The Odds API.
        
    Raises:
        ValueError: If an unsupported league is provided.
    """
    league_lower = league.lower()
    if league_lower == 'nba':
        return 'basketball_nba'
    elif league_lower == 'wnba':
        return 'basketball_wnba'
    else:
        raise ValueError(f"Unsupported league for odds extraction: {league}")

def fetch_odds(sport_key: str) -> dict:
    """
    Makes the HTTP GET request to The Odds API to fetch live odds.
    
    Args:
        sport_key (str): The specific sport key (e.g., 'basketball_nba').
        
    Returns:
        dict: The JSON response parsed into a Python dictionary.
        
    Raises:
        RuntimeError: If the API request fails or the API key is missing.
    """
    if not API_KEY:
        raise RuntimeError("ODDS_API_KEY is not set. Please ensure it is present in your .env file or system environment.")
        
    print(f" -> [API Call] Fetching live odds for {sport_key}...")
    
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    
    params = {
        'apiKey': API_KEY,
        'regions': REGIONS,
        'markets': MARKETS,
        'oddsFormat': ODDS_FORMAT,
        'dateFormat': DATE_FORMAT,
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch odds. Status Code: {response.status_code}, Response: {response.text}")
        
    # Log usage statistics provided by The Odds API headers
    print(f" -> [Success] Remaining API Requests: {response.headers.get('x-requests-remaining')}")
    print(f" -> [Success] Used API Requests: {response.headers.get('x-requests-used')}")
    
    return response.json()

def process_odds_data(odds_json: list) -> pd.DataFrame:
    """
    Flattens the deeply nested JSON response into a structured Pandas DataFrame.
    
    Args:
        odds_json (list): The raw JSON list of games and odds.
        
    Returns:
        pd.DataFrame: A structured dataframe ready for match-making.
    """
    print(" -> Processing and flattening nested odds data...")
    games_data = []
    
    for game in odds_json:
        game_id = game.get("id")
        sport_key = game.get("sport_key")
        commence_time = game.get("commence_time")
        home_team = game.get("home_team")
        away_team = game.get("away_team")
        
        # We iterate over all bookmakers dynamically extracted from the JSON
        for bookmaker in game.get("bookmakers", []):
            bookmaker_title = bookmaker.get("title")
            
            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                
                for outcome in market.get("outcomes", []):
                    team_name = outcome.get("name")
                    price = outcome.get("price")
                    point = outcome.get("point") # Only exists for spreads/totals
                    
                    games_data.append({
                        "GAME_ID": game_id,
                        "SPORT_KEY": sport_key,
                        "COMMENCE_TIME": commence_time,
                        "HOME_TEAM": home_team,
                        "AWAY_TEAM": away_team,
                        "BOOKMAKER": bookmaker_title,
                        "MARKET_TYPE": market_key,
                        "TARGET_TEAM": team_name,
                        "PRICE": price,
                        "POINT": point
                    })
                    
    return pd.DataFrame(games_data)

# =============================================================================
# MASTER ORCHESTRATOR FUNCTION (The Engine)
# =============================================================================
def run_odds_pipeline(league: str) -> None:
    """
    Master orchestrator for The Odds API data extraction.
    Injects the correct sport key based on the league and saves the structured CSV.
    
    Args:
        league (str): The targeted league identifier ('nba' or 'wnba').
    """
    print(f"\n[Odds API] Starting odds extraction pipeline for {league.upper()}...")
    
    try:
        # 1. Parameter resolution
        sport_key = get_sport_key(league)
        
        # 2. Sequential Data Extraction
        raw_odds = fetch_odds(sport_key)
        
        # 3. Data Transformation (JSON to Pandas)
        df_odds = process_odds_data(raw_odds)
        
        # 4. File System Operations
        output_dir = Path("data/raw")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"odds_{league.lower()}.csv"
        df_odds.to_csv(output_file, index=False)
        
        print(f"✅ [Odds API] Successfully cached {len(df_odds)} odds rows for {league.upper()} into {output_file}")
        
    except Exception as e:
        raise RuntimeError(f"Failed to complete odds pipeline for {league.upper()}: {e}")

# --------------------------- local tests ------------------------------------
if __name__ == "__main__":
    print("--- The Odds API Local Integration Check ---")
    
    # Simulating standard main.py user inputs
    test_league = "wnba" # Switch to 'nba' to test the men's league
    
    try:
        # run_odds_pipeline(league=test_league) # Uncomment this to test a real API call locally
        print("\n✅ Local pipeline code syntax validation completed.")
    except Exception as e:
        print(f"\n❌ Pipeline failed during testing: {e}")