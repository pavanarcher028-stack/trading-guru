import warnings
warnings.filterwarnings("ignore")
import pandas as pd
import numpy as np
import requests

def get_live_rate():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
        rate = float(r.json()["rates"]["INR"])
        print("[BACKTEST] Live USD/INR: " + str(rate), flush=True)
        return rate
    except:
        return 84.0

def get_signals(df):
    close = df["close"]
    ema9 = close.ewm(span=9).mean()
    ema21 = close.ewm(span=21).mean()
    ema200 = close.ewm(span=200).mean()
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(25).mean()
    loss = -delta.where(delta < 0, 0.0).rolling(25).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    signals = pd.Series(0, index=df.index)
    buy = (ema9 > ema21) & (close > ema200) & (rsi < 30)
    signals[buy] = 1
    sell = (rsi > 80) | (ema9 < ema21)
    signals[sell] = -1
    return signals

def run_backtest(strategy_code, all_data):
    usd_to_inr = get_live_rate()
    results = {}
    for coin, df in all_data.items():
        try:
            signals = get_signals(df)
            capital = 10000
            position = 0
            buy_price = 0
            hold_count = 0
            trades = []
            peak = capital
            max_drawdown = 0
            for i in range(1, len(signals)):
                price = float(df["close"].iat[i])
                sig = int(signals.iat[i])
                if sig == 1 and position == 0:
                    position = capital / price
                    buy_price = price
                    hold_count = 0
                elif position > 0:
                    hold_count += 1
                    pct = (price - buy_price) / buy_price * 100
                    if pct <= -4.0 or pct >= 8.0 or hold_count >= 48 or sig == -1:
                        sell_value = position * price
                        profit = sell_value - capital
                        trades.append(profit)
                        capital = sell_value
                        position = 0
                        buy_price = 0
                        hold_count = 0
                current_equity = capital + (position * price if position > 0 else 0)
                if current_equity > peak:
                    peak = current_equity
                dd = ((peak - current_equity) / peak) * 100
                if dd > max_drawdown:
                    max_drawdown = dd
            if len(trades) == 0:
                results[coin] = {"sharpe": 0, "win_rate": 0, "max_drawdown": 100, "trades": 0, "passed": False}
                continue
            trades_arr = np.array(trades)
            wins = len(trades_arr[trades_arr > 0])
            win_rate = round(wins / len(trades_arr) * 100, 1)
            avg = np.mean(trades_arr)
            std = np.std(trades_arr)
            sharpe = round(avg / std if std > 0 else 0, 2)
            max_drawdown = round(max_drawdown, 2)
            passed = win_rate >= 55.0 and max_drawdown <= 20.0 and len(trades) >= 3
            results[coin] = {"sharpe": sharpe, "win_rate": win_rate, "max_drawdown": max_drawdown, "trades": len(trades), "passed": passed}
            status = "PASS" if passed else "FAIL"
            price_inr = round(float(df["close"].iloc[-1]) * usd_to_inr, 2)
            print(coin + " [" + status + "] Sharpe: " + str(sharpe) + " Win: " + str(win_rate) + "% DD: " + str(max_drawdown) + "% Trades: " + str(len(trades)) + " Price: Rs." + str(price_inr), flush=True)
        except Exception as e:
            print("Backtest failed for " + coin + ": " + str(e), flush=True)
            results[coin] = {"sharpe": 0, "win_rate": 0, "max_drawdown": 100, "trades": 0, "passed": False}
    return results

def is_strategy_good(results):
    good_coins = []
    for coin, score in results.items():
        if score["passed"]:
            good_coins.append(coin)
            print(coin + " approved for live trading", flush=True)
    if not good_coins:
        print("No coins passed", flush=True)
    return good_coins
