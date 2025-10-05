import pandas as pd
from pathlib import Path
import sys
from plotly.subplots import make_subplots
import plotly.graph_objects as go


def main():
    pf = Path('data/processed/coingecko_bitcoin_market_chart_last365d_1D.parquet')
    out = Path('docs/images/candlestick_sample.png')
    if not pf.exists():
        print('ERROR: parquet file not found:', pf.resolve())
        sys.exit(2)

    df = pd.read_parquet(pf)
    # Ensure datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
                df = df.set_index('datetime')
            else:
                df.reset_index(inplace=True)
                df['datetime'] = pd.to_datetime(df.iloc[:,0])
                df = df.set_index('datetime')

    # Ensure MA columns exist
    for w in (7, 30):
        col = f'MA{w}'
        if col not in df.columns:
            df[col] = df['close'].rolling(w).mean()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='OHLC'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA7'], mode='lines', name='MA7', line=dict(color='blue')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA30'], mode='lines', name='MA30', line=dict(color='orange')), row=1, col=1)
    # volume
    if 'volume' in df.columns:
        fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume', marker=dict(color='lightgray')), row=2, col=1)

    fig.update_layout(title='BTC Daily Candlestick + MA7/MA30', xaxis_rangeslider_visible=False, width=1200, height=700)

    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.write_image(str(out))
        print('Wrote image:', out.resolve())
    except Exception as e:
        print('Failed to write PNG (kaleido might be missing):', e)
        out_html = out.with_suffix('.html')
        fig.write_html(str(out_html))
        print('Wrote interactive HTML instead:', out_html.resolve())


if __name__ == '__main__':
    main()
