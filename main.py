"""
=============================================================================
MEEWMA 3.0: MASTER ORCHESTRATOR
=============================================================================
This is the central execution pipeline for the MeewMa ecosystem. 
It features an interactive Command Line Interface (CLI) to capture 
target parameters (League, Season Phase) and securely routes them 
downwards to the extraction, processing, and matching layers.
"""

import sys
import time

# --- Layer Imports (SSOT Architecture) ---
# Importing the master functions natively instead of using fragile subprocesses.
try:
    from src.data_extraction.nba_stats import run_stats_pipeline
    from src.data_extraction.odds_api import run_odds_pipeline
    from src.data_processing.data_processor import run_processing_pipeline
    from src.data_processing.match_maker import run_matching_pipeline
    from src.arbitrage_engine.delta_analyzer import fetch_draftea_sheet, calculate_market_deltas
except ImportError as e:
    print(f"\n[CRITICAL ERROR] Failed to import pipeline modules. Verify your folder structure. Details: {e}")
    sys.exit(1)

# =============================================================================
# CLI & USER EXPERIENCE (UX)
# =============================================================================
def display_header():
    """Renders the ecosystem header for professional terminal UX."""
    print("\n" + "="*60)
    print(" 🏀 MEEWMA 3.0: ARBITRAGE SYSTEM ORCHESTRATOR 🏀 ")
    print("="*60)

def prompt_league_selection() -> str:
    """Interactively requests the target league from the operator."""
    while True:
        print("\n[STEP 1] Select Target Market:")
        print("  [1] NBA (Men's Professional Basketball)")
        print("  [2] WNBA (Women's Professional Basketball)")
        choice = input(" -> Enter choice (1 or 2): ").strip()
        
        if choice == '1':
            return 'nba'
        elif choice == '2':
            return 'wnba'
        else:
            print(" [!] Invalid selection. Please enter 1 or 2.")

def prompt_season_phase() -> str:
    """Interactively requests the season phase to calibrate the lookback window."""
    while True:
        print("\n[STEP 2] Select Season Phase (Calibrates Variance Model):")
        print("  [1] Regular Season (Standard 7-game lookback)")
        print("  [2] Playoffs (Aggressive 3-game lookback)")
        print("  [3] Pre Season")
        choice = input(" -> Enter choice (1, 2, or 3): ").strip()
        
        if choice == '1':
            return 'Regular Season'
        elif choice == '2':
            return 'Playoffs'
        elif choice == '3':
            return 'Pre Season'
        else:
            print(" [!] Invalid selection. Please enter 1, 2, or 3.")

# =============================================================================
# MASTER EXECUTION THREAD
# =============================================================================
def main():
    display_header()
    
    # 1. Capture Dynamic Parameters from User
    target_league = prompt_league_selection()
    target_phase = prompt_season_phase()
    
    print("\n" + "="*60)
    print(f" 🚀 INITIATING PIPELINE | MARKET: {target_league.upper()} | PHASE: {target_phase} ")
    print("="*60)
    
    start_time = time.time()
    
    try:
        # ---------------------------------------------------------
        # LAYER 1: DATA EXTRACTION (APIs)
        # ---------------------------------------------------------
        print("\n[>>>] EXECUTING LAYER 1: EXTRACTION ENGINE")
        run_stats_pipeline(league=target_league, season_type=target_phase)
        run_odds_pipeline(league=target_league)
        
        # ---------------------------------------------------------
        # LAYER 2: DATA PROCESSING (Math & Feature Engineering)
        # ---------------------------------------------------------
        print("\n[>>>] EXECUTING LAYER 2: PROCESSING ENGINE")
        run_processing_pipeline(league=target_league, season_type=target_phase)
        
        # ---------------------------------------------------------
        # LAYER 3: THE BRIDGE (Match Making & Distribution Routing)
        # ---------------------------------------------------------
        print("\n[>>>] EXECUTING LAYER 3: MATCH-MAKER ENGINE")
        run_matching_pipeline(league=target_league)
        
        # ---------------------------------------------------------
        # PIPELINE COMPLETION
        # ---------------------------------------------------------
        elapsed_time = time.time() - start_time
        print("\n" + "="*60)
        print(f" 🟢 PIPELINE COMPLETED SUCCESSFULLY IN {elapsed_time:.2f} SECONDS 🟢")
        print(" -> Output Matrices ready in /data/targets/")
        print(" -> Ecosystem is primed for the Mathematical Tridents.")
        print("="*60 + "\n")
        
    except Exception as e:
        # Global Fail-Fast Architecture: Stops the entire system if one layer corrupts
        print("\n" + "!"*60)
        print(" 🛑 FAIL-FAST TRIGGERED: PIPELINE ABORTED 🛑 ")
        print(f" -> Critical Exception: {e}")
        print("!"*60 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()