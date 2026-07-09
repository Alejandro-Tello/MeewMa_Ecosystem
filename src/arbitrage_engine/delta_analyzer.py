"""
MeewMa 3.0 - Arbitrage Engine: Delta Analyzer
This module is responsible for bridging minimal manual inputs (from Soft books like Draftea)
with automated Sharp consensus data. It calculates structural pricing lags and line deltas
to identify mathematically profitable betting opportunities (EV+).
"""

import pandas as pd
import numpy as np
from thefuzz import process

def fetch_draftea_sheet(sheet_url: str) -> pd.DataFrame:
    """
    Reads the minimal manual inputs from a public Google Sheet.
    Expects only: team_name, line_value, draftea_over_odds, draftea_under_odds.
    
    Parameters:
    -----------
    sheet_url : str
        The shareable Google Sheets URL.
        
    Returns:
    --------
    pd.DataFrame
        Raw dataframe containing the user's minimal manual inputs.
    """
    if "edit?usp=sharing" in sheet_url:
        csv_url = sheet_url.replace("edit?usp=sharing", "export?format=csv")
    elif "edit#" in sheet_url:
        csv_url = sheet_url.split("edit#")[0] + "export?format=csv"
    else:
        csv_url = sheet_url

    try:
        df = pd.read_csv(csv_url)
        # Clean potential whitespace from manual entry
        df['team_name'] = df['team_name'].astype(str).str.strip()
        return df
    except Exception as e:
        raise IOError(f"Failed to fetch manual data from pipeline: {str(e)}")

def inject_sharp_consensus(draftea_df: pd.DataFrame, sharp_df: pd.DataFrame, threshold: int = 80) -> pd.DataFrame:
    """
    Fuzzy matches the minimal team names inputted by the user with the official 
    Sharp consensus data to inject 'game_id' and 'sharp_line_consensus' automatically.
    
    Parameters:
    -----------
    draftea_df : pd.DataFrame
        The minimal manual input DataFrame.
    sharp_df : pd.DataFrame
        The automated consensus DataFrame from odds_api.py.
    threshold : int
        Minimum fuzzy match score (0-100) to accept a team name pairing.
        
    Returns:
    --------
    pd.DataFrame
        Enriched DataFrame containing both soft lines and sharp consensus.
    """
    enriched_df = draftea_df.copy()
    sharp_teams = sharp_df['team_name'].tolist()
    
    game_ids = []
    sharp_lines = []
    
    for team in enriched_df['team_name']:
        # Extract the best match using Levenshtein distance
        best_match, score = process.extractOne(team, sharp_teams)
        
        if score >= threshold:
            # Retrieve the corresponding sharp data for the matched team
            match_row = sharp_df[sharp_df['team_name'] == best_match].iloc[0]
            game_ids.append(match_row['game_id'])
            sharp_lines.append(match_row['sharp_line_consensus'])
        else:
            # Defensive programming: If user made a huge typo, flag as NaN to drop later
            game_ids.append(np.nan)
            sharp_lines.append(np.nan)
            
    enriched_df['game_id'] = game_ids
    enriched_df['sharp_line_consensus'] = sharp_lines
    
    # Drop rows where fuzzy matching failed to prevent data contamination
    return enriched_df.dropna(subset=['sharp_line_consensus'])

def calculate_market_deltas(market_df: pd.DataFrame) -> pd.DataFrame:
    """
    Executes vectorized calculations to discover information lags (Deltas).
    A positive delta indicates the Soft line is lower than the Sharp consensus (Over opportunity).
    A negative delta indicates the Soft line is higher (Under opportunity).
    
    Parameters:
    -----------
    market_df : pd.DataFrame
        The enriched dataframe containing matched Soft and Sharp data.
        
    Returns:
    --------
    pd.DataFrame
        Final dataframe sorted by the magnitude of the arbitrage opportunity.
    """
    analysis_df = market_df.copy()

    # 1. Calculate Line Delta (Sharp Line - Soft Line)
    analysis_df['line_delta'] = analysis_df['sharp_line_consensus'] - analysis_df['line_value']

    # 2. Determine raw directional bias
    analysis_df['directional_bias'] = np.where(
        analysis_df['line_delta'] > 0, 'OVER_BIAS',
        np.where(analysis_df['line_delta'] < 0, 'UNDER_BIAS', 'NEUTRAL')
    )

    # 3. Absolute Delta for sorting priority (Magnitude of the lag)
    analysis_df['priority_score'] = analysis_df['line_delta'].abs()

    # Sort to surface the most aggressive discrepancies first
    return analysis_df.sort_values(by='priority_score', ascending=False).reset_index(drop=True)

if __name__ == "__main__":
    print("--- Running delta_analyzer.py Integration Test ---")
    
    # 1. Mocking the API output (What python downloads automatically in the background)
    mock_sharp_data = pd.DataFrame({
        'game_id': ['20261105_BOS_LAL', '20261105_NYK_MIA'],
        'team_name': ['Boston Celtics', 'New York Knicks'],
        'sharp_line_consensus': [112.5, 105.0]
    })
    
    # 2. Mocking your manual input (What you type in Google Sheets from your phone)
    mock_draftea_input = pd.DataFrame({
        'team_name': ['Celtics', 'Celtics', 'Knicks', 'Lakers'], # Note the abbreviations
        'line_value': [110.5, 111.5, 107.5, 115.0],
        'draftea_over_odds': [1.85, 1.95, 1.90, 1.85],
        'draftea_under_odds': [1.85, 1.75, 1.80, 1.85]
    })
    
    print("\n1. Injecting Sharp Consensus via Fuzzy Matching...")
    enriched_data = inject_sharp_consensus(mock_draftea_input, mock_sharp_data)
    
    print("\n2. Calculating Deltas...")
    final_deltas = calculate_market_deltas(enriched_data)
    
    print("\n[ FINAL ARBITRAGE TARGETS ]")
    print(final_deltas[['team_name', 'game_id', 'line_value', 'sharp_line_consensus', 'line_delta', 'directional_bias']])