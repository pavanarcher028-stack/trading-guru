import requests
import pandas as pd
import time

COINS = {
    "BTC": "B-BTC_USDT",
    "ETH": "B-ETH_USDT",
    "BNB": "B-BNB_USDT",
    "SOL": "B-SOL_USDT",
    "XRP": "B-XRP_USDT"
}

def get_ohlcv(symbol, pair):
    try:
        url = "https://public.coindcx.com/market_data/candles"
        params = {
            "pair": pair,
            "interval": "1h",
            "limit": 1000
        }
        response = requests.get(url, params=params, timeout=15)
        print("[DATA] " + pair + " status: " + str(response.status_code), flush=True)

        data = response.json()

        if not data or len(data) == 0:
            print("[DATA] Empty response for " + pair, flush=True)
            return None

        if isinstance(data, dict):
            print("[DATA] Error response for " + pair + ": " + str(data), flush=True)
            return None

        df = pd.DataFrame(data)
        print("[DATA] Columns: " + str(list(df.columns)), flush=True)

        if "time" in df.columns:
            df = df.rename(columns={"time": "timestamp"})

        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp")
        df.set_index("timestamp", inplace=True)
        df = df[["open", "high", "low", "close", "volume"]].astype(float)

        print("[DATA] OK " + pair + " — " + str(len(df)) + " candles — last close: " + str(df["close"].iloc[-1]), flush=True)
        return df

    except Exception as e:
        print("[DATA] Failed " + pair + ": " + str(e), flush=True)
        return None

def get_top5_ohlcv():
    all_data = {}
    for symbol, pair in COINS.items():
        print("[DATA] Fetching " + symbol + " (" + pair + ")...", flush=True)
        df = get_ohlcv(symbol, pair)
        if df is not None:
            all_data[symbol] = df
        time.sleep(1)
    print("[DATA] Done — " + str(len(all_data)) + "/5 coins fetched", flush=True)
    return all_data

def get_market_summary(all_data):
    summary = []
    for coin, df in all_data.items():
        last_close = round(df["close"].iloc[-1], 4)
        change = round(
            ((df["close"].iloc[-1] - df["close"].iloc[-2])
            / df["close"].iloc[-2]) * 100, 2
        )
        summary.append(coin + ": price=" + str(last_close) + ", change=" + str(change) + "%")
    result = "\n".join(summary)
    print("[DATA] Summary:\n" + result, flush=True)
    return result
def get_usd_to_inr():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=10)
        data = response.json()
        rate = float(data["rates"]["INR"])
        print("[DATA] Live USD/INR rate: " + str(rate), flush=True)
        return rate
    except Exception as e:
        print("[DATA] Rate fetch failed, using 84.0: " + str(e), flush=True)
        return 84.0
