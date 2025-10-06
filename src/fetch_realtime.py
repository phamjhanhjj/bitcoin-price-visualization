import requests
import pandas as pd
from datetime import datetime, timedelta
import time

_CACHE = {}

def fetch_realtime_data(coin="bitcoin", currency="usd", minutes=60, cache_seconds=300):
    """Lấy dữ liệu realtime gần đây (last N minutes)."""
    key = (coin, currency, minutes)
    now = time.time()
    if key in _CACHE:
        ts, df = _CACHE[key]
        if now - ts < cache_seconds:
            return df

    days = max(1, minutes // 1440)  # CoinGecko chỉ cho days
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
    params = {"vs_currency": currency, "days": days}

    resp = requests.get(url, params=params)
    data = resp.json()

    if "prices" not in data:
        raise ValueError(f"Lỗi API: {data}")

    df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)

    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    df = df[df.index >= cutoff]

    _CACHE[key] = (now, df)
    return df


def fetch_realtime_range(coin="bitcoin", currency="usd", start=None, end=None, cache_seconds=300):
    """Lấy dữ liệu theo khoảng start–end datetime."""
    if start is None or end is None:
        raise ValueError("Cần truyền start và end datetime")

    key = (coin, currency, start, end)
    now = time.time()
    if key in _CACHE:
        ts, df = _CACHE[key]
        if now - ts < cache_seconds:
            return df

    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart/range"
    params = {"vs_currency": currency, "from": int(start.timestamp()), "to": int(end.timestamp())}

    resp = requests.get(url, params=params)
    data = resp.json()

    if "prices" not in data:
        raise ValueError(f"Lỗi API: {data}")

    df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)

    _CACHE[key] = (now, df)
    return df