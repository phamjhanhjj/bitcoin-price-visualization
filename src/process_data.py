import json
import os
import pandas as pd
import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
RAW_DIR = os.path.join(ROOT, 'data', 'raw')
PROCESSED_DIR = os.path.join(ROOT, 'data', 'processed')
os.makedirs(PROCESSED_DIR, exist_ok=True)

def detect_ts_unit(series):
    # simple heuristic: values > 1e12 are ms
    if series.max() > 1e12:
        return 'ms'
    return 's'

def load_market_chart_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        j = json.load(f)
    prices = pd.DataFrame(j.get('prices', []), columns=['timestamp','price'])
    if prices.empty:
        return pd.DataFrame()
    unit = detect_ts_unit(prices['timestamp'])
    prices['datetime'] = pd.to_datetime(prices['timestamp'], unit=('ms' if unit=='ms' else 's'), utc=True)
    prices.set_index('datetime', inplace=True)
    prices = prices.drop(columns=['timestamp'])
    vols = pd.DataFrame(j.get('total_volumes', []), columns=['timestamp','volume'])
    if not vols.empty:
        vunit = detect_ts_unit(vols['timestamp'])
        vols['datetime'] = pd.to_datetime(vols['timestamp'], unit=('ms' if vunit=='ms' else 's'), utc=True)
        vols.set_index('datetime', inplace=True)
        vols = vols.drop(columns=['timestamp'])
        df = prices.join(vols, how='left')
    else:
        df = prices
    return df.sort_index()

def load_ohlc_json(path):
    with open(path,'r',encoding='utf-8') as f:
        arr = json.load(f)
    df = pd.DataFrame(arr, columns=['timestamp','open','high','low','close'])
    unit = detect_ts_unit(df['timestamp'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit=('ms' if unit=='ms' else 's'), utc=True)
    df.set_index('datetime', inplace=True)
    return df[['open','high','low','close']].sort_index()

def resample_to_ohlc(df, rule='1D'):
    # df expected to have 'price' and optional 'volume'
    if 'price' not in df.columns:
        raise ValueError('DataFrame must contain price column to create OHLC')
    agg = df['price'].resample(rule).agg(['first','max','min','last']).rename(columns={
        'first':'open','max':'high','min':'low','last':'close'
    })
    if 'volume' in df.columns:
        agg['volume'] = df['volume'].resample(rule).sum()
    agg.dropna(inplace=True)
    return agg

def add_features(df):
    df = df.copy()
    df['pct_change'] = df['close'].pct_change() * 100
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    df['MA7'] = df['close'].rolling(window=7).mean()
    df['MA30'] = df['close'].rolling(window=30).mean()
    # annualized vol: sqrt(365) for daily returns
    df['vol_30d'] = df['log_return'].rolling(window=30).std() * np.sqrt(365)
    return df

def process_and_save(input_path, out_name=None, resample_rule='1D'):
    # detect whether file is market_chart or ohlc by opening and inspecting
    with open(input_path,'r',encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict) and 'prices' in data:
        df = load_market_chart_json(input_path)
        df_ohlc = resample_to_ohlc(df, rule=resample_rule)
    else:
        # assume ohlc list
        df_ohlc = load_ohlc_json(input_path)
    df_feat = add_features(df_ohlc)
    if out_name is None:
        base = os.path.basename(input_path).replace('.json','')
        out_name = f"{base}_{resample_rule}.parquet"
    out_path = os.path.join(PROCESSED_DIR, out_name)
    df_feat.to_parquet(out_path)
    return out_path

if __name__ == '__main__':
    print('process_data module loaded')
