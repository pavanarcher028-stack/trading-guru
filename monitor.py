import json
import os
from datetime import datetime

LOG_FILE = "performance_log.json"

def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    return {
        "trades": [],
        "total_pnl": 0,
        "win_count": 0,
        "loss_count": 0,
        "consecutive_losses": 0,
        "strategy_version": 1
    }

def save_log(log):
    with open(LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2)

def record_trade(coin, action, entry_price, exit_price, amount):
    log = load_log()

    if entry_price is None or exit_price is None:
        return

    pnl = (exit_price - entry_price) * amount
    pnl = round(pnl, 2)
    won = pnl > 0

    trade = {
        "coin": coin,
        "entry": entry_price,
        "exit": exit_price,
        "pnl": pnl,
        "won": won,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    log["trades"].append(trade)
    log["total_pnl"] = round(log["total_pnl"] + pnl, 2)

    if won:
        log["win_count"] += 1
        log["consecutive_losses"] = 0
    else:
        log["loss_count"] += 1
        log["consecutive_losses"] += 1

    save_log(log)
    status = "WIN" if won else "LOSS"
    print(f"Trade recorded [{status}] {coin} → PnL: ₹{pnl}")

def get_performance_summary():
    log = load_log()
    total = log["win_count"] + log["loss_count"]

    if total == 0:
        return "No trades recorded yet"

    win_rate = round((log["win_count"] / total) * 100, 1)

    summary = f"""
    Total trades   : {total}
    Win rate       : {win_rate}%
    Total PnL      : ₹{log['total_pnl']}
    Wins           : {log['win_count']}
    Losses         : {log['loss_count']}
    Consec. losses : {log['consecutive_losses']}
    Strategy ver.  : {log['strategy_version']}
    """
    print(summary)
    return summary

def needs_regeneration(log=None):
    if log is None:
        log = load_log()

    total = log["win_count"] + log["loss_count"]

    # not enough data yet
    if total < 5:
        return False

    win_rate = (log["win_count"] / total) * 100

    # trigger regeneration if any of these are true
    if win_rate < 55:
        print(f"Win rate dropped to {round(win_rate,1)}% — regenerating strategy")
        return True

    if log["consecutive_losses"] >= 3:
        print(f"3 consecutive losses — regenerating strategy")
        return True

    if log["total_pnl"] < -500:
        print(f"Total PnL below -₹500 — regenerating strategy")
        return True

    return False

def bump_strategy_version():
    log = load_log()
    log["strategy_version"] += 1
    log["consecutive_losses"] = 0
    save_log(log)
    print(f"Strategy upgraded to version {log['strategy_version']}")
