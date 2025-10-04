import pandas as pd
import json
import numpy as np
from pathlib import Path

PROCESSED = Path(__file__).resolve().parents[1] / 'data' / 'processed'
P = PROCESSED / 'coingecko_bitcoin_market_chart_last365d_1D.parquet'

def main():
    df = pd.read_parquet(P)
    df.index = pd.to_datetime(df.index)
    start = str(df.index.min())
    end = str(df.index.max())
    n = len(df)
    desc = df['close'].describe().to_dict()
    df['pct_change'] = df['close'].pct_change() * 100
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    mean_return = float(df['pct_change'].mean())
    median_return = float(df['pct_change'].median())
    std_return = float(df['pct_change'].std())
    vol_30d = df['log_return'].rolling(window=30).std().iloc[-1] * np.sqrt(365)
    vol_30d = None if pd.isna(vol_30d) else float(vol_30d)
    cummax = df['close'].cummax()
    drawdown = (df['close'] / cummax) - 1
    max_dd = float(drawdown.min())
    top_up = df['pct_change'].nlargest(5).tolist()
    top_down = df['pct_change'].nsmallest(5).tolist()
    res = {
        'file': str(P),
        'start': start,
        'end': end,
        'n': n,
        'describe_close': desc,
        'mean_pct_change': mean_return,
        'median_pct_change': median_return,
        'std_pct_change': std_return,
        'vol_30d_annualized': vol_30d,
        'max_drawdown': max_dd,
        'top_5_up_pct': top_up,
        'top_5_down_pct': top_down
    }
    OUT = PROCESSED / 'analysis_summary.json'
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print('Saved', OUT)

if __name__ == '__main__':
    main()
