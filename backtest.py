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


def run_backtest(strategy_code, all_data):
    usd_to_inr = get_live_rate()
    results = {}
    for coin, df in all_data.items():
        try:
            local_env = {}
            exec(strategy_code, local_env)
            get_signals = local_env["get_signals"]
            raw = get_signals(df.copy())
            if isinstance(raw, pd.DataFrame):
                raw = raw.iloc[:, 0]
            raw = pd.Series(raw).reset_index(drop=True)
            signals = pd.to_numeric(raw, errors="coerce").fillna(0)
            close = df["close"].reset_index(drop=True)
            capital = 10000.0
            position = 0.0
            buy_price = 0.0
            hold_count = 0
            trades = []
            equity = [capital]
            for i in range(1, len(signals)):
                price = float(close.iat[i])
                try:
                    val = float(signals.iat[i])
                except:
                    val = 0.0
                if val > 0:
                    sig = 1
                elif val < 0:
                    sig = -1
                else:
                    sig = 0
                if sig == 1 and position == 0.0:
                    position = capital / price
                    buy_price = price
                    hold_count = 0
                elif position > 0.0:
                    hold_count += 1
                    pct = (price - buy_price) / buy_price * 100.0
                    if pct <= -3.0 or pct >= 6.0 or hold_count >= 48 or sig == -1:
                        new_capital = position * price
                        profit = new_capital - capital
                        trades.append(profit)
                        capital = new_capital
                        position = 0.0
                        buy_price = 0.0
                        hold_count = 0
                if position > 0.0:
                    current = position * price
                else:
                    current = capital
                equity.append(current)
            equity = np.array(equity)
            peak = np.maximum.accumulate(equity)
            drawdowns = (peak - equity) / peak * 100.0
            max_drawdown = round(float(np.max(drawdowns)), 2)
            if len(trades) == 0:
                results[coin] = {"sharpe": 0, "win_rate": 0, "max_drawdown": max_drawdown, "trades": 0, "passed": False}
                continue
            trades_arr = np.array(trades)
            wins = int(np.sum(trades_arr > 0))
            win_rate = round(wins / len(trades_arr) * 100.0, 1)
            avg = float(np.mean(trades_arr))
            std = float(np.std(trades_arr))
            sharpe = round(avg / std if std > 0 else 0.0, 2)
            passed = sharpe >= 0.5 and win_rate >= 55.0 and max_drawdown <= 20.0 and len(trades) >= 5
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
