import streamlit as st
import os
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime
from src.viz import plot_candlestick_plotly

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / 'data' / 'processed'

st.set_page_config(layout='wide')
st.title('BTC Visualization Dashboard (CoinGecko)')

st.sidebar.header('Data')
files = list(PROCESSED_DIR.glob('*.parquet')) if PROCESSED_DIR.exists() else []
# allow multi-select to compare coins/files
file_choices = st.sidebar.multiselect('Processed file(s) (select 1 or more)', options=[str(f.name) for f in files], default=[str(files[-1].name)] if files else [])

file_choice = file_choices[0] if file_choices else None

if not file_choice:
    st.info('No processed files found. Run the processing script to create data in data/processed.')
    st.stop()

@st.cache_data
def load_parquet(path):
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index)
    return df

df = load_parquet(PROCESSED_DIR / file_choice)

st.sidebar.header('Range')
min_date = df.index.min().date()
max_date = df.index.max().date()
# date range slider (more interactive)
start, end = st.sidebar.slider('Date range', value=(min_date, max_date), min_value=min_date, max_value=max_date)

# function to load and filter a parquet file (cached above)
def load_and_filter(name, start_date, end_date):
    path = PROCESSED_DIR / name
    d = load_parquet(path)
    d = d.loc[(d.index.date >= start_date) & (d.index.date <= end_date)]
    return d

# support multiple selections
dfs = {}
for name in file_choices:
    dfs[name] = load_and_filter(name, start, end)

# choose main df for single-file flows
df_sel = dfs[file_choice] if file_choice else pd.DataFrame()

st.sidebar.header('Chart options')
ma_short = st.sidebar.number_input('MA short window', min_value=1, max_value=200, value=7)
ma_long = st.sidebar.number_input('MA long window', min_value=1, max_value=400, value=30)
resample_option = st.sidebar.selectbox('Resample interval (note: limited by source granularity)', options=['None','1D','12H','6H','4H','1H'])
show_ma = st.sidebar.checkbox('Show moving averages', value=True)
show_volume = st.sidebar.checkbox('Show volume (candlestick)', value=True)
compare_mode = st.sidebar.selectbox('Compare mode', options=['None','Overlay','Indexed (base=100)','Separate axes'])
normalize = st.sidebar.checkbox('Normalize closes to 100 (for compare)', value=False)

with st.sidebar.expander('Settings'):
    csv_float_format = st.checkbox('CSV floats as 6 decimal places', value=True)

# If data has only OHLC already, resampling 'None' uses existing
df_work = df_sel.copy()
if resample_option != 'None':
    # If the processed file already has OHLC columns use them; else try to resample from price
    if set(['open','high','low','close']).issubset(df_work.columns):
        # resample OHLC
        try:
            df_work = df_work.resample(resample_option).agg({
                'open':'first','high':'max','low':'min','close':'last','volume':'sum'
            })
        except Exception:
            st.warning('Resample failed: check source index frequency and granularity')
    elif 'price' in df_work.columns:
        try:
            df_work = df_work['price'].resample(resample_option).agg(['first','max','min','last'])
            df_work.columns = ['open','high','low','close']
        except Exception:
            st.warning('Resample from price failed: check source index frequency and granularity')

df_work.dropna(inplace=True)

st.header('Price (Close)')
col1, col2 = st.columns([3,1])
with col1:
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=df_work.index, y=df_work['close'], name='Close'))
    if show_ma and 'close' in df_work.columns:
        fig_line.add_trace(go.Scatter(x=df_work.index, y=df_work['close'].rolling(window=ma_short).mean(), name=f'MA{ma_short}'))
        fig_line.add_trace(go.Scatter(x=df_work.index, y=df_work['close'].rolling(window=ma_long).mean(), name=f'MA{ma_long}'))
    fig_line.update_layout(height=350, margin={'l':20,'r':20,'t':30,'b':20})
    st.plotly_chart(fig_line, use_container_width=True)
with col2:
    st.metric('Start', str(df_work.index.min().date()) if not df_work.empty else '-')
    st.metric('End', str(df_work.index.max().date()) if not df_work.empty else '-')

if 'close' in df_work.columns and compare_mode == 'None' and len(file_choices) <= 1:
    # compute moving averages dynamically for display
    df_display = df_work.copy()
    df_display[f'MA{ma_short}'] = df_display['close'].rolling(window=ma_short).mean()
    df_display[f'MA{ma_long}'] = df_display['close'].rolling(window=ma_long).mean()
    st.subheader('Close with MAs')
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=df_display.index, y=df_display['close'], name='Close'))
    if show_ma:
        fig_line.add_trace(go.Scatter(x=df_display.index, y=df_display[f'MA{ma_short}'], name=f'MA{ma_short}'))
        fig_line.add_trace(go.Scatter(x=df_display.index, y=df_display[f'MA{ma_long}'], name=f'MA{ma_long}'))
    st.plotly_chart(fig_line, use_container_width=True)

# If multiple files selected or compare mode requested, build comparison chart
if compare_mode != 'None' or len(file_choices) > 1:
    st.subheader('Comparison')
    comp_fig = go.Figure()
    # build series for each file
    for name, d in dfs.items():
        if d.empty or 'close' not in d.columns:
            continue
        series = d['close'].copy()
        if compare_mode == 'Indexed (base=100)' or normalize:
            base = series.iloc[0]
            series = (series / base) * 100
        comp_fig.add_trace(go.Scatter(x=series.index, y=series.values, name=name.replace('.parquet','')))
    comp_fig.update_layout(height=450, margin={'l':20,'r':20,'t':30,'b':20})
    st.plotly_chart(comp_fig, use_container_width=True)

st.header('Candlestick')
if set(['open','high','low','close']).issubset(df_work.columns):
    fig = plot_candlestick_plotly(df_work, title=f'Candlestick ({resample_option})')
    if show_volume and 'volume' in df_work.columns:
        fig.add_trace(go.Bar(x=df_work.index, y=df_work['volume'], name='Volume', marker={'color':'lightgrey'}, yaxis='y2'))
        fig.update_layout(yaxis2=dict(overlaying='y', side='right', showgrid=False, position=0.15))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info('No OHLC data available for candlestick. Try resampling from price or use a processed file with OHLC.')

st.header('Statistics')
st.write(df_work.describe())

# Export
from io import BytesIO
if not df_work.empty:
    csv_buf = BytesIO()
    if csv_float_format:
        df_work.to_csv(csv_buf, float_format='%.6f')
    else:
        df_work.to_csv(csv_buf)
    csv_buf.seek(0)
    st.download_button('Download CSV', data=csv_buf, file_name=f'{file_choice.replace(".parquet","")}_{resample_option}.csv', mime='text/csv')

    pq_buf = BytesIO()
    df_work.to_parquet(pq_buf)
    pq_buf.seek(0)
    st.download_button('Download Parquet', data=pq_buf, file_name=f'{file_choice.replace(".parquet","")}_{resample_option}.parquet', mime='application/octet-stream')

    # Download current figure as PNG (if available)
    try:
        # prioritize comparison fig if present
        target_fig = comp_fig if ('comp_fig' in locals() and comp_fig.data) else (fig if 'fig' in locals() else None)
        if target_fig is not None:
            img_bytes = target_fig.to_image(format='png')
            st.download_button('Download chart PNG', data=img_bytes, file_name='chart.png', mime='image/png')
    except Exception as e:
        st.info('PNG export requires the `kaleido` package for Plotly; install it if you want PNG export. Error: ' + str(e))
