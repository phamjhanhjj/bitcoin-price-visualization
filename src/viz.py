import matplotlib.pyplot as plt
import mplfinance as mpf
import plotly.graph_objects as go
import pandas as pd

def plot_line_with_mas(df, title='Close + MAs'):
    plt.figure(figsize=(12,6))
    plt.plot(df.index, df['close'], label='Close')
    if 'MA7' in df.columns:
        plt.plot(df.index, df['MA7'], label='MA7')
    if 'MA30' in df.columns:
        plt.plot(df.index, df['MA30'], label='MA30')
    plt.title(title)
    plt.xlabel('Date'); plt.ylabel('Price (USD)')
    plt.legend(); plt.grid(True)
    plt.show()

def plot_return_hist(df, col='pct_change'):
    plt.figure(figsize=(8,4))
    plt.hist(df[col].dropna(), bins=80)
    plt.title('Histogram of daily % change')
    plt.show()

def plot_candlestick_mpl(df, title='Candlestick'):
    # mplfinance expects columns open,high,low,close and optional volume
    plot_df = df.copy()
    mpf.plot(plot_df, type='candle', volume=('volume' in plot_df.columns), mav=(7,30), title=title)

def plot_candlestick_plotly(df, title='Candlestick'):
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close']
    )])
    fig.update_layout(title=title, xaxis_rangeslider_visible=False)
    return fig
