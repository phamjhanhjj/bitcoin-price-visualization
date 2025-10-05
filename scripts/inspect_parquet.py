import sys
from pathlib import Path
import pandas as pd

def main():
    pf = Path('data/processed/coingecko_bitcoin_market_chart_last365d_1D.parquet')
    if not pf.exists():
        print(f'ERROR: file not found: {pf.resolve()}')
        sys.exit(2)

    df = pd.read_parquet(pf)
    print('File:', pf)
    print('Shape:', df.shape)
    print('\nColumns:', list(df.columns))
    print('\nDtypes:')
    print(df.dtypes)
    print('\nHead:')
    print(df.head(10).to_string())

    # Basic stats for common columns
    for col in ['close','price','pct_change','log_return','volume']:
        if col in df.columns:
            print(f'\n--- Stats for {col} ---')
            print(df[col].describe())

    out = Path('data/processed/sample_coingecko_100.csv')
    df.head(100).to_csv(out, index=True)
    print(f'\nWrote sample CSV: {out.resolve()}')

if __name__ == '__main__':
    main()
