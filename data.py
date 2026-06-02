import sys
sys.stdout.reconfigure(line_buffering=True)

import ccxt
import pandas as pd

print("[DATA] Initializing Binance connection...")

try:
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot'
        }
    })
    print("[DATA] Binance connected successfully")
except Exception as e:
    print(f"[DATA] Binance connection failed: {e}")

COINS = [
    'BTC/USDT',
    'ETH/USDT',
    'XRP/USDT',
    'DOGE/USDT',
    'MATIC/USDT'
]

def get_top5_ohlcv():
    all_data = {}
    for coin in COINS:
        try:
            print(f"[DATA] Fetching {coin}...")
            ohlcv = exchange.fetch_ohlcv(coin, timeframe='1h', limit=200)
            if not ohlcv:
                print(f"[DATA] Empty response for {coin}")
                continue
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp','open','high','low','close','volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            all_data[coin] = df
            print(f"[DATA] OK {coin} — {len(df)} candles — last close: {df['close'].iloc[-1]}")
        except Exception as e:
            print(f"[DATA] FAILED {coin}: {e}")
    print(f"[DATA] Done — fetched {len(all_data)}/5 coins")
    return all_data

def get_market_summary(all_data):
    summary = []
    for coin, df in all_data.items():
        last_close = round(df['close'].iloc[-1], 4)
        change = round(
            ((df['close'].iloc[-1] - df['close'].iloc[-24])
            / df['close'].iloc[-24]) * 100, 2
        )
        vol = round(df['volume'].iloc[-1], 2)
        summary.append(
            f"{coin}: price={last_close}, 24h_change={change}%, volume={vol}"
        )
    result = "\n".join(summary)
    print(f"[DATA] Market summary:\n{result}")
    return result
