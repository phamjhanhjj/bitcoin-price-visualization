import json
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / 'data' / 'processed'
DOCS_DIR = ROOT / 'docs'
DOCS_DIR.mkdir(exist_ok=True)

# find bitcoin parquet (prefer filename containing "bitcoin")
parquets = list(PROCESSED_DIR.glob('*.parquet'))
btc_file = None
for p in parquets:
    if 'bitcoin' in p.name.lower():
        btc_file = p
        break
if btc_file is None:
    raise SystemExit('No bitcoin parquet found in data/processed. Run processing first.')

print('Loading', btc_file)
df = pd.read_parquet(btc_file)
df.index = pd.to_datetime(df.index)

# Ensure close column
if 'close' not in df.columns:
    raise SystemExit('Processed file does not contain close prices.')

# Basic stats
start = df.index.min()
end = df.index.max()
count = len(df)
na_count = df['close'].isna().sum()
min_price = float(df['close'].min())
max_price = float(df['close'].max())
median_price = float(df['close'].median())
mean_price = float(df['close'].mean())
std_price = float(df['close'].std())

# returns
df['pct_change'] = df['close'].pct_change()
df['log_return'] = np.log(df['close'] / df['close'].shift(1))

returns = df['pct_change'].dropna()
logr = df['log_return'].dropna()

ret_stats = {
    'mean_pct': float(returns.mean()) * 100,
    'median_pct': float(returns.median()) * 100,
    'std_pct': float(returns.std()) * 100,
    'skewness': float(returns.skew()),
    'kurtosis': float(returns.kurt())
}

log_stats = {
    'mean_log': float(logr.mean()),
    'std_log': float(logr.std()),
    'annualized_vol_30d': float(logr.rolling(window=30).std().mean() * np.sqrt(365))
}

# max drawdown
cum = (1 + logr).cumprod()
rolling_max = cum.cummax()
drawdown = cum / rolling_max - 1
max_dd = float(drawdown.min())

# longest drawdown duration (in days)
dd_end = drawdown.idxmin()
# find last peak before dd_end
peak_idx = (cum[:dd_end]).idxmax()
dd_duration = (dd_end - peak_idx).days

# recent performance
recent_30d = df['close'].iloc[-30:]
recent_change_30d = (recent_30d.iloc[-1] / recent_30d.iloc[0] - 1) * 100 if len(recent_30d) >= 2 else None

analysis = {
    'file': str(btc_file),
    'range_start': str(start),
    'range_end': str(end),
    'count': int(count),
    'na_count': int(na_count),
    'min_price': min_price,
    'max_price': max_price,
    'median_price': median_price,
    'mean_price': mean_price,
    'std_price': std_price,
    'returns': ret_stats,
    'log_return': log_stats,
    'max_drawdown': max_dd,
    'drawdown_end': str(dd_end),
    'drawdown_start_peak': str(peak_idx),
    'drawdown_duration_days': dd_duration,
    'recent_30d_change_pct': float(recent_change_30d) if recent_change_30d is not None else None
}

# write JSON
out_json = PROCESSED_DIR / (btc_file.stem + '_analysis.json')
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(analysis, f, indent=2)
print('Wrote analysis JSON to', out_json)

# Create Markdown doc
md = []
md.append('# Code & Data Analysis — Bitcoin')
md.append('Generated file: ' + str(out_json))
md.append('\n## 1) Project code overview')
md.append('This project contains the following important modules:')
md.append('\n- `src/fetch_data.py`: helpers to fetch raw JSON from CoinGecko (market_chart, ohlc). Includes `fetch_market_chart_range_chunked` and `fetch_recent_market_chart`. Saves raw JSON in `data/raw/` and metadata in `data/raw/meta/`.')
md.append('\n- `src/process_data.py`: parse raw JSON to pandas DataFrame, detect timestamp unit (ms vs s), resample to OHLC (via `resample_to_ohlc`), and compute features (pct_change, log_return, MA7, MA30, volatility). Exposes `process_and_save` to save a processed Parquet file in `data/processed/`.')
md.append('\n- `src/viz.py`: plotting helpers (Plotly and mplfinance). `plot_candlestick_plotly` returns a Plotly Figure.')
md.append('\n- `src/dashboard.py`: Streamlit dashboard to inspect processed data, compare files, and export CSV/Parquet/PNG. Uses caching to speed loads.')
md.append('\n- `src/generate_analysis.py`: this analysis generator (loads processed parquet and writes analysis JSON + docs).')

md.append('\n## 2) Data file analyzed')
md.append(f'- Processed file: `{btc_file.name}`')
md.append(f'- Date range: **{start.date()}** to **{end.date()}**')
md.append(f'- Data points: **{count}** (missing close: {na_count})')

md.append('\n## 3) Price statistics')
md.append(f'- Min price: {min_price:,.2f} USD')
md.append(f'- Max price: {max_price:,.2f} USD')
md.append(f'- Median price: {median_price:,.2f} USD')
md.append(f'- Mean price: {mean_price:,.2f} USD')
md.append(f'- Std dev (price): {std_price:,.2f} USD')

md.append('\n## 4) Return statistics (daily)')
md.append(f'- Mean daily % change: {ret_stats["mean_pct"]:.4f}%')
md.append(f'- Median daily % change: {ret_stats["median_pct"]:.4f}%')
md.append(f'- Std daily % change: {ret_stats["std_pct"]:.4f}%')
md.append(f'- Skewness: {ret_stats["skewness"]:.4f}')
md.append(f'- Kurtosis: {ret_stats["kurtosis"]:.4f}')

md.append('\n## 5) Log-return & volatility')
md.append(f'- Mean log-return (daily): {log_stats["mean_log"]:.6f}')
md.append(f'- Std log-return (daily): {log_stats["std_log"]:.6f}')
md.append(f'- Average 30-day rolling annualized vol (approx): {log_stats["annualized_vol_30d"]:.4f}')

md.append('\n## 6) Drawdown')
md.append(f'- Max drawdown (fraction): {max_dd:.4f} ({max_dd*100:.2f}%)')
md.append(f'- Drawdown period: peak at {peak_idx.date()} to trough at {dd_end.date()} ({dd_duration} days)')

md.append('\n## 7) Recent performance')
md.append(f'- 30-day change: {analysis["recent_30d_change_pct"]:.4f}%')

md.append('\n## 8) Notes and recommendations')
md.append('- This analysis is computed on the processed OHLC series. If your processed file is daily resampled, the statistics are daily-based.\n- For higher-frequency insights (intraday), keep raw OHLC from the `ohlc` endpoint or fetch exchange data.\n- Check for survivorship / missing data: some days may be dropped during resample.\n- For forecasting or risk models, consider additional features (volume skew, realized vol, ADR, GARCH models).')

md.append('\n---\nGenerated by `src/generate_analysis.py`')

md_path = DOCS_DIR / 'code_and_data_analysis.md'
with open(md_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(md))
print('Wrote markdown to', md_path)
