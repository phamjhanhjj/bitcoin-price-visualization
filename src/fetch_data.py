import time
import json
import os
from pycoingecko import CoinGeckoAPI
from datetime import datetime
import calendar
import requests
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT, "data", "raw")
METADATA_DIR = os.path.join(ROOT, "data", "raw", "meta")

cg = CoinGeckoAPI()

def save_json(obj, fname):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, fname), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def save_meta(meta, fname):
    os.makedirs(METADATA_DIR, exist_ok=True)
    with open(os.path.join(METADATA_DIR, fname), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def fetch_market_chart_range(coin_id="bitcoin", vs_currency="usd", from_dt=None, to_dt=None):
    """
    from_dt, to_dt: datetime objects (UTC)
    Saves raw JSON and metadata. Returns path to saved JSON.
    """
    if from_dt is None or to_dt is None:
        raise ValueError("from_dt and to_dt are required datetime objects (UTC)")
    from_unix = int(calendar.timegm(from_dt.timetuple()))
    to_unix   = int(calendar.timegm(to_dt.timetuple()))
    print(f"Fetch market_chart range {coin_id} {from_unix} -> {to_unix}")
    try:
        res = cg.get_coin_market_chart_range_by_id(id=coin_id, vs_currency=vs_currency,
                                                   from_timestamp=from_unix, to_timestamp=to_unix)
    except requests.exceptions.HTTPError as e:
        # attempts to unwrap API error message (pycoingecko wraps HTTP errors into ValueError sometimes)
        msg = str(e)
        raise RuntimeError("CoinGecko HTTP error: " + msg)
    except ValueError as e:
        # pycoingecko raises ValueError with API JSON on some errors
        msg = str(e)
        if 'exceeds the allowed time range' in msg or '10012' in msg:
            raise RuntimeError(
                'CoinGecko Public API limits historical range for public users to the past 365 days. '
                'Your requested from/to range is older than that.\n'
                'Workarounds: (1) request a range within the last 365 days, (2) use the `fetch_recent_market_chart` helper for last-N-days, '\
                '(3) upgrade to a paid CoinGecko plan, or (4) use an exchange API (e.g., Binance) for full historical data.'
            )
        raise
    fname = f"coingecko_{coin_id}_market_chart_{from_unix}_{to_unix}.json"
    save_json(res, fname)
    meta = {
        "coin_id": coin_id,
        "vs_currency": vs_currency,
        "endpoint": "market_chart_range",
        "from": from_unix,
        "to": to_unix,
        "fetched_at": int(time.time())
    }
    save_meta(meta, fname + ".meta.json")
    return os.path.join(DATA_DIR, fname)

def fetch_ohlc(coin_id="bitcoin", vs_currency="usd", days=30):
    """days can be 1,7,14,30,90,180,365,max — returns list of [ts,open,high,low,close]"""
    print(f"Fetch ohlc {coin_id} {days}d")
    res = cg.get_coin_ohlc_by_id(id=coin_id, vs_currency=vs_currency, days=days)
    fname = f"coingecko_{coin_id}_ohlc_{days}d.json"
    save_json(res, fname)
    meta = {
        "coin_id": coin_id,
        "vs_currency": vs_currency,
        "endpoint": "ohlc",
        "days": days,
        "fetched_at": int(time.time())
    }
    save_meta(meta, fname + ".meta.json")
    return os.path.join(DATA_DIR, fname)


def fetch_recent_market_chart(coin_id="bitcoin", vs_currency="usd", days=90):
    """Convenience helper: fetch market_chart for the last `days` using CoinGecko `market_chart` endpoint.
    This avoids using the range endpoint (which may be restricted for older history).
    days can be 1,7,14,30,90,180,365,max (subject to API limits).
    """
    print(f"Fetch recent market_chart {coin_id} last {days} days")
    res = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency=vs_currency, days=days)
    fname = f"coingecko_{coin_id}_market_chart_last{days}d.json"
    save_json(res, fname)
    meta = {
        "coin_id": coin_id,
        "vs_currency": vs_currency,
        "endpoint": "market_chart",
        "days": days,
        "fetched_at": int(time.time())
    }
    save_meta(meta, fname + ".meta.json")
    return os.path.join(DATA_DIR, fname)


def fetch_market_chart_range_chunked(coin_id="bitcoin", vs_currency="usd", from_dt=None, to_dt=None, chunk_days=365, pause_sec=1, merge=True):
    """Fetch a long historical range by splitting into chunks each at most `chunk_days` long.

    Args:
        coin_id, vs_currency: as usual
        from_dt, to_dt: datetime objects (UTC)
        chunk_days: max days per chunk (default 365 to respect public API)
        pause_sec: pause between requests to be polite
        merge: if True, merge all 'prices' and 'total_volumes' into a single JSON and save as combined file

    Returns:
        list of saved chunk file paths; if merge True also returns merged filepath as last element.
    """
    if from_dt is None or to_dt is None:
        raise ValueError('from_dt and to_dt are required datetime objects (UTC)')
    if to_dt <= from_dt:
        raise ValueError('to_dt must be after from_dt')

    delta = to_dt - from_dt
    total_days = delta.days + 1
    saved = []
    chunk_start = from_dt
    while chunk_start < to_dt:
        chunk_end = min(chunk_start + pd.Timedelta(days=chunk_days) - pd.Timedelta(seconds=1), to_dt)
        try:
            path = fetch_market_chart_range(coin_id=coin_id, vs_currency=vs_currency, from_dt=chunk_start, to_dt=chunk_end)
        except RuntimeError as e:
            # bubble up but include chunk info
            raise RuntimeError(f'Chunk fetch failed for {chunk_start} -> {chunk_end}: {e}')
        saved.append(path)
        time.sleep(pause_sec)
        chunk_start = chunk_end + pd.Timedelta(seconds=1)

    if merge:
        # merge JSONs by concatenating 'prices' and 'total_volumes'
        merged = {'prices': [], 'market_caps': [], 'total_volumes': []}
        for p in saved:
            with open(p, 'r', encoding='utf-8') as f:
                j = json.load(f)
            for k in ['prices','market_caps','total_volumes']:
                if k in j:
                    merged[k].extend(j[k])
        # deduplicate by timestamp for prices & volumes
        def uniq_sorted(arr):
            seen = set()
            out = []
            for ts, val in arr:
                if ts not in seen:
                    seen.add(ts)
                    out.append([ts,val])
            out.sort(key=lambda x: x[0])
            return out

        merged['prices'] = uniq_sorted(merged.get('prices', []))
        merged['market_caps'] = uniq_sorted(merged.get('market_caps', []))
        merged['total_volumes'] = uniq_sorted(merged.get('total_volumes', []))

        merged_fname = f"coingecko_{coin_id}_market_chart_{int(calendar.timegm(from_dt.timetuple()))}_{int(calendar.timegm(to_dt.timetuple()))}_merged.json"
        save_json(merged, merged_fname)
        meta = {
            'coin_id': coin_id,
            'vs_currency': vs_currency,
            'endpoint': 'market_chart_range_merged',
            'from': int(calendar.timegm(from_dt.timetuple())),
            'to': int(calendar.timegm(to_dt.timetuple())),
            'chunks': len(saved),
            'fetched_at': int(time.time())
        }
        save_meta(meta, merged_fname + '.meta.json')
        saved.append(os.path.join(DATA_DIR, merged_fname))

    return saved

if __name__ == '__main__':
    # simple demo (won't run in import)
    from datetime import datetime
    p = fetch_market_chart_range('bitcoin','usd', datetime(2021,1,1), datetime(2021,12,31))
    print('Saved:', p)
