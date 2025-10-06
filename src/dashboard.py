import streamlit as st
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta
from viz import plot_candlestick_plotly
from fetch_realtime import fetch_realtime_data, fetch_realtime_range

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / 'data/processed'

st.set_page_config(layout='wide')
st.title('BTC Visualization Dashboard (CoinGecko)')

# === Sidebar: Data Mode ===
st.sidebar.header("Data Mode")
mode = st.sidebar.radio("Select data mode", ["Offline", "Realtime (last N minutes)", "Custom Range"])

# === Load Data ===
if mode == "Realtime (last N minutes)":
    minutes = st.sidebar.slider("Lookback minutes", 15, 1440, 60, step=15)
    try:
        df = fetch_realtime_data("bitcoin", "usd", minutes=minutes, cache_seconds=300)
    except Exception as e:
        st.error(f"Cannot fetch realtime data: {e}")
        st.stop()
elif mode == "Custom Range":
    start_date = st.sidebar.date_input("Start date", datetime.utcnow().date() - timedelta(days=7))
    end_date = st.sidebar.date_input("End date", datetime.utcnow().date())
    if start_date > end_date:
        st.error("Start date must be before End date")
        st.stop()
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    try:
        df = fetch_realtime_range("bitcoin", "usd", start=start_dt, end=end_dt, cache_seconds=300)
    except Exception as e:
        st.error(f"Cannot fetch custom range data: {e}")
        st.stop()
else:  # Offline
    files = list(PROCESSED_DIR.glob('*.parquet')) if PROCESSED_DIR.exists() else []
    file_choices = st.sidebar.multiselect(
        'Processed file(s)',
        options=[str(f.name) for f in files],
        default=[str(files[-1].name)] if files else []
    )
    if not file_choices:
        st.info('No processed files found.')
        st.stop()
    file_choice = file_choices[0]

    @st.cache_data
    def load_parquet(path):
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        return df

    df = load_parquet(PROCESSED_DIR / file_choice)
    # Range filter
    min_date = df.index.min().date()
    max_date = df.index.max().date()
    start, end = st.sidebar.slider(
        'Select range',
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date)
    )
    df = df.loc[(df.index.date >= start) & (df.index.date <= end)]

# === Chart Options ===
st.sidebar.header('Chart Options')
ma_short = st.sidebar.number_input('MA short window', 1, 200, 7)
ma_long = st.sidebar.number_input('MA long window', 1, 400, 30)
resample_option = st.sidebar.selectbox('Resample interval', ['None','1D','12H','6H','4H','1H'])
show_close = st.sidebar.checkbox('Show Close', True)
show_ma_short = st.sidebar.checkbox('Show MA Short', True)
show_ma_long = st.sidebar.checkbox('Show MA Long', True)
show_bb_upper = st.sidebar.checkbox('Show BB Upper', True)
show_bb_lower = st.sidebar.checkbox('Show BB Lower', True)
show_volume = st.sidebar.checkbox('Show Volume', True)

# === Resample if needed ===
df_work = df.copy()
if resample_option != 'None' and not df_work.empty:
    if set(['open','high','low','close']).issubset(df_work.columns):
        df_work = df_work.resample(resample_option).agg({
            'open':'first','high':'max','low':'min','close':'last','volume':'sum'
        })
    elif 'price' in df_work.columns:
        df_work = df_work['price'].resample(resample_option).agg(['first','max','min','last'])
        df_work.columns = ['open','high','low','close']

df_work.dropna(inplace=True)

# === Compute indicators ===
if 'close' not in df_work.columns and 'price' in df_work.columns:
    df_work['close'] = df_work['price']

df_work['MA_short'] = df_work['close'].rolling(ma_short).mean()
df_work['MA_long'] = df_work['close'].rolling(ma_long).mean()
df_work['BB_mid'] = df_work['close'].rolling(20).mean()
df_work['BB_std'] = df_work['close'].rolling(20).std()
df_work['BB_upper'] = df_work['BB_mid'] + 2*df_work['BB_std']
df_work['BB_lower'] = df_work['BB_mid'] - 2*df_work['BB_std']

df_work['pct_change'] = df_work['close'].pct_change()
df_work['log_return'] = np.log(df_work['close']/df_work['close'].shift(1))
cum = (1 + df_work['pct_change']).cumprod()
df_work['drawdown'] = cum / cum.cummax() - 1
df_work['rolling_vol_30d'] = df_work['log_return'].rolling(30).std() * np.sqrt(365)

# RSI 14
delta = df_work['close'].diff()
up = delta.clip(lower=0)
down = -delta.clip(upper=0)
roll_up = up.rolling(14).mean()
roll_down = down.rolling(14).mean()
RS = roll_up / roll_down
df_work['RSI'] = 100 - (100 / (1 + RS))

# Trading Signals (MA crossover + RSI + Bollinger)
signals = []
for i in range(len(df_work)):
    sig = "Hold"
    if i>0:
        if df_work['MA_short'].iloc[i] > df_work['MA_long'].iloc[i] and df_work['MA_short'].iloc[i-1] <= df_work['MA_long'].iloc[i-1]:
            sig = "Buy"
        elif df_work['MA_short'].iloc[i] < df_work['MA_long'].iloc[i] and df_work['MA_short'].iloc[i-1] >= df_work['MA_long'].iloc[i-1]:
            sig = "Sell"
        if df_work['RSI'].iloc[i] < 30:
            sig = "Buy"
        elif df_work['RSI'].iloc[i] > 70:
            sig = "Sell"
        if df_work['close'].iloc[i] < df_work['BB_lower'].iloc[i]:
            sig = "Buy"
        elif df_work['close'].iloc[i] > df_work['BB_upper'].iloc[i]:
            sig = "Sell"
    signals.append(sig)
df_work['Signal'] = signals

# === Price & Indicators plot ===
st.header('Price & Technical Indicators')
fig_price = go.Figure()
if show_close:
    fig_price.add_trace(go.Scatter(x=df_work.index, y=df_work['close'], name='Close'))
if show_ma_short:
    fig_price.add_trace(go.Scatter(x=df_work.index, y=df_work['MA_short'], name=f'MA{ma_short}'))
if show_ma_long:
    fig_price.add_trace(go.Scatter(x=df_work.index, y=df_work['MA_long'], name=f'MA{ma_long}'))
if show_bb_upper:
    fig_price.add_trace(go.Scatter(x=df_work.index, y=df_work['BB_upper'], name='BB Upper', line=dict(dash='dot', color='red')))
if show_bb_lower:
    fig_price.add_trace(go.Scatter(x=df_work.index, y=df_work['BB_lower'], name='BB Lower', line=dict(dash='dot', color='red')))
st.plotly_chart(fig_price, use_container_width=True)

# === Candlestick ===
st.header('Candlestick Chart')
if set(['open','high','low','close']).issubset(df_work.columns):
    fig_candle = plot_candlestick_plotly(df_work)
    if show_volume and 'volume' in df_work.columns:
        fig_candle.add_trace(go.Bar(x=df_work.index, y=df_work['volume'], name='Volume', marker={'color':'lightgrey'}, yaxis='y2'))
        fig_candle.update_layout(yaxis2=dict(overlaying='y', side='right', showgrid=False, position=0.15))
    st.plotly_chart(fig_candle, use_container_width=True)

# === Log-return Histogram ===
st.header('Log-Return Histogram')
fig_hist = go.Figure()
fig_hist.add_trace(go.Histogram(x=df_work['log_return'], nbinsx=50))
st.plotly_chart(fig_hist, use_container_width=True)

# === Drawdown ===
st.header('Drawdown Chart')
fig_dd = go.Figure()
fig_dd.add_trace(go.Scatter(x=df_work.index, y=df_work['drawdown'], fill='tozeroy', name='Drawdown'))
st.plotly_chart(fig_dd, use_container_width=True)

# === Rolling Volatility ===
st.header('30-Day Rolling Volatility')
fig_vol = go.Figure()
fig_vol.add_trace(go.Scatter(x=df_work.index, y=df_work['rolling_vol_30d'], name='Rolling Volatility'))
st.plotly_chart(fig_vol, use_container_width=True)

# === RSI ===
st.header('RSI 14')
fig_rsi = go.Figure()
fig_rsi.add_trace(go.Scatter(x=df_work.index, y=df_work['RSI'], name='RSI'))
st.plotly_chart(fig_rsi, use_container_width=True)

# === Trading Signals Table ===
st.header('Trading Signals (Last 50 rows)')
st.dataframe(df_work[['close','MA_short','MA_long','RSI','BB_upper','BB_lower','Signal']].tail(50))

# === Statistics Summary ===
st.header('Statistics Summary')
st.write(df_work.describe())
