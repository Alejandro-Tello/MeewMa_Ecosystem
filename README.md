# Data-Driven Market Inefficiency Detection System (MeewMa 3.0)

An advanced sports analytics and quantitative financial arbitrage engine designed to systematically identify and exploit real-time market discrepancies (Positive Expected Value, EV+) between global "Sharp" sportsbooks (Pinnacle/Bet365 consensus) and regional "Soft" recreational platforms (Draftea).

## 🏀 System Vision & Strategy
Unlike traditional predictive machine learning models that focus solely on forecasting winners, MeewMa 3.0 operates as an information-arbitrage pipeline. It intercepts market lines in real time, leveraging a technical lag tracker to detect latency discrepancies caused by the structural infrastructure differences of soft books.

## 🛠️ System Architecture

The project follows a modular **Clean Architecture** layout structured under strict data immutability and high-performance vectorized operations.

```text
meewma-ecosystem/
│
├── data/
│   ├── raw/                  # Unmodified source data JSONs/CSVs
│   └── processed/            # Cleaned, rhythm-normalized datasets
│
├── src/
│   ├── data_ingestion/       # Layer 1: API connections (odds_api.py, nba_stats.py)
│   ├── data_processing/      # Layer 2: Vectorized transformations (data_processor.py)
│   ├── arbitrage_engine/     # Layer 3: Lag profiling & fuzzing (delta_analyzer.py)
│   └── models/               # Layer 4: Mathematical trident (poisson_model.py)
│
├── .env                      # Protected environment variables
├── .gitignore                # Security boundaries against raw data leaks
└── main.py                   # Central orchestrator & interactive terminal menu
Key Technical Capabilities ImplementedFail-Fast Automated Orchestration (main.py): Central interactive terminal menu allowing dynamic descend-injection of targets (League: NBA/WNBA and Season Phase: Regular Season/Playoffs/Pre-Season). Enforces a strict fail-fast policy via an absolute try-except master block.Dynamic Data Ingestion Pipeline (src/data_ingestion/): Autonomous extractors targeting nba_api endpoints and The Odds API. It dynamically computes current fiscal years via specialized lookup utilities, bypassing hardcoded configurations, and relies on defensive programming against JSON/HTML anomalies.Vectorized Contextual Pre-processing (src/data_processing/): Built entirely using Pandas vector operations. Implements hierarchical context imputation for NaN handling (using collective system averages), uniform pace normalization (scaling count metrics to 100 possessions), and a rolling time lookback window to filter out data obsolescence.High-Performance Entity Resolution (src/arbitrage_engine/): Employs Levenshtein distance metrics via thefuzz[speedup] (compiled in C) at a strict threshold ($\ge 80\%$) to match asymmetric casino naming conventions against official league registries vectorially. Supports contextual target identification via MATCH_TOTAL and TEAM_TOTAL logic maps.Automated Statistical Segmentation Switch: Features an automated statistical router based on the Coefficient of Variation ($CV = \sigma / \mu$). Players and teams with stable distribution vectors ($CV < 0.25$) are routed into the Poisson Model (using a vectorized Cumulative Distribution Function via scipy.stats.poisson), while volatile assets ($CV \ge 0.25$) are prepared for the Negative Binomial Distribution.🚀 Technical StackLanguage: Python 3.11+Data Science & Analytics: Pandas, NumPy, Scipy (Stats module)API & Data Stream Ingestion: Requests, Google Sheets Flat-CSV endpoints, nba_api, python-dotenvString Metric Algorithms: thefuzz (Levenshtein distance compiled in C)Local Infrastructure Optimization: pathlib for smart calendar caching controls.⚙️ Installation & SetupClone the Repository:Bashgit clone [https://github.com/Alejandro-Tello/MeewMa_Ecosystem.git](https://github.com/Alejandro-Tello/MeewMa_Ecosystem.git)
cd MeewMa_Ecosystem
Environment Variables Configuration:Create a .env file in the root directory:Fragmento de códigoODDS_API_KEY=your_api_key_here
DRAFTEA_SHEET_URL=[https://docs.google.com/spreadsheets/d/.../export?format=csv](https://docs.google.com/spreadsheets/d/.../export?format=csv)
Run Package Environment:Execute via uv or standard virtual environment manager:Bashuv run python main.py
⚖️ License & Usage RestrictionsCopyright (c) 2026 Alejandro. All rights reserved.This software, methodology, and its associated architecture documentation are provided strictly for personal, non-commercial use as a private engineering portfolio demonstration.You may not use, reproduce, distribute, or modify this system for commercial purposes or financial gain.You may not package, monetize, or offer this codebase (or derivatives of it) as a service or subscription product to any third parties.
