import pandas as pd
import numpy as np


def run_backtest(strategy_code, all_data):
    results = {}
    for coin, df in all_data.items():
        try:
            local_env = {}
            exec(strategy_code, local_env)
            get_signals = local_env["get_signals"]
            signals = get_signals(df)
            capital = 10000
            position = 0
            buy_price = 0
            trades = []
            equity_curve = [capital]
            peak = capital
            max_drawdown = 0
            for i in range(1, len(signals)):
                price = float(df["close"].iloc[i])
                sig = int(signals.iloc[i])
                if sig == 1 and position == 0:
                    position = capital / price
                    buy_price = price
                elif sig == -1 and position > 0:
                    sell_value = position * price
                    profit = sell_value - capital
                    trades.append(profit)
                    capital = sell_value
                    position = 0
                current_equity = capital + (position * price if position > 0 else 0)
                equity_curve.append(current_equity)
                if current_equity > peak:
                    peak = current_equity
                dd = ((peak - current_equity) / peak) * 100
                if dd > max_drawdown:
                    max_drawdown = dd
            if len(trades) == 0:
                results[coin] = {"sharpe": 0, "win_rate": 0, "max_drawdown": 100, "trades": 0, "passed": False}
                continue
            trades_arr = np.array(trades)
            win_rate = round(len(trades_arr[trades_arr > 0]) / len(trades_arr) * 100, 1)
            avg = np.mean(trades_arr)
            std = np.std(trades_arr)
            sharpe = round(