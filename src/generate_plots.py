from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / 'data' / 'processed'
IMG_DIR = ROOT / 'docs' / 'images'
IMG_DIR.mkdir(parents=True, exist_ok=True)

# find bitcoin parquet
parquets = list(PROCESSED_DIR.glob('*.parquet'))
btc_file = None
for p in parquets:
    if 'bitcoin' in p.name.lower():
        btc_file = p
        break
if btc_file is None:
    raise SystemExit('No bitcoin parquet found in data/processed')

print('Loading', btc_file)
df = pd.read_parquet(btc_file)
df.index = pd.to_datetime(df.index)

if 'close' not in df.columns:
    raise SystemExit('No close column')

# returns
returns = df['close'].pct_change().dropna()
# histogram
plt.figure(figsize=(8,4))
plt.hist(returns, bins=80, color='tab:blue', alpha=0.8)
plt.title('Histogram of daily returns')
plt.xlabel('Daily return')
plt.ylabel('Frequency')
plt.grid(True)
hist_path = IMG_DIR / 'returns_histogram.png'
plt.savefig(hist_path, bbox_inches='tight', dpi=150)
plt.close()
print('Saved', hist_path)

# volatility (30-day rolling std of log returns, annualized)
logr = np.log(df['close'] / df['close'].shift(1)).dropna()
vol30 = logr.rolling(window=30).std() * np.sqrt(365)
plt.figure(figsize=(10,4))
plt.plot(vol30.index, vol30, color='tab:orange')
plt.title('30-day rolling annualized volatility (approx)')
plt.xlabel('Date')
plt.ylabel('Annualized vol')
plt.grid(True)
vol_path = IMG_DIR / 'vol30_timeseries.png'
plt.savefig(vol_path, bbox_inches='tight', dpi=150)
plt.close()
print('Saved', vol_path)
