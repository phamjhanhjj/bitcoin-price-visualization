# BTC Visualization (CoinGecko)

This project fetches market data from CoinGecko, processes it into OHLC/time-series, computes features (returns, moving averages, volatility), and provides visualizations including an interactive Streamlit dashboard.

See the `src/` scripts for fetch/processing/visualization helpers.

Quick start

1. Create virtual env and activate (Windows PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

2. Fetch data (example):

```powershell
python -c "from src.fetch_data import fetch_market_chart_range; from datetime import datetime; fetch_market_chart_range('bitcoin','usd', datetime(2021,1,1), datetime(2021,12,31))"
```

3. Process data:

```powershell
python -c "from src.process_data import load_market_chart_json, process_and_save; process_and_save('data/raw/coingecko_bitcoin_market_chart_...json')"
```

4. Run dashboard:

```powershell
streamlit run src/dashboard.py
```

Notes
- Keep raw JSON in `data/raw/` for reproducibility.
- Check metadata in `metadata.json` after fetches.

Important: CoinGecko historical range limits
-------------------------------------------------
CoinGecko's public API limits historical queries for public users to the past 365 days. If you request a range older than 365 days using the `market_chart/range` endpoint you may see an error like:

	"Your request exceeds the allowed time range. Public API users are limited to querying historical data within the past 365 days."

Workarounds:
- Request shorter ranges within the last 365 days.
- Use the `fetch_recent_market_chart` helper in `src/fetch_data.py` to fetch the last-N-days (easier for rolling pulls).
- Upgrade to a paid CoinGecko plan if you need full historical coverage.
- Use an exchange API (e.g., Binance) for full OHLC historical data at fine granularity.

Docker (optional)

Build the image and run Streamlit inside a container (example):

```powershell
docker build -t btc-viz:latest .
docker run -p 8501:8501 --rm btc-viz:latest
```

Then open http://localhost:8501 in your browser.
