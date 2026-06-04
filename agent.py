import sys
import threading
from api import start_api
import os
import time
import requests
from data import get_top5_ohlcv, get_market_summary
from backtest import run_backtest, is_strategy_good
from trader import execute_strategy
from monitor import needs_regeneration, bump_strategy_version, get_performance_summary

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
print("TRADING AGENT STARTED", flush=True)


def build_prompt(market_summary):
    p = "You are an expert quant trading strategy developer for crypto.\n"
    p += "Market data: " + market_summary + "\n"
    p += "Write a Python function get_signals(df).\n"
    p += "df has columns: open, high, low, close, volume.\n"
    p += "Return pandas Series: 1=buy, -1=sell, 0=hold.\n"
    p += "Use EMA crossover and RSI. Only pandas and numpy.\n"
    p += "Return ONLY the raw Python function. No markdown.\n"
    return p


def build_fix_prompt(market_summary, strategy_code, failed_tests):
    p = "Fix this Python trading function:\n"
    p += strategy_code + "\n"
    p += "These coins failed:\n"
    for f in failed_tests:
        p += f["coin"] + " failed " + f["test"] + " got " + f["value"] + "\n"
    p += "Fix only the weak parts. Return ONLY the function. No markdown.\n"
    return p


def clean_code(full):
    if "```python" in full:
        code = full.split("```python")[1].split("```")[0].strip()
    elif "```" in full:
        code = full.split("```")[1].split("```")[0].strip()
    elif "def get_signals" in full:
        idx = full.index("def get_signals")
        code = full[idx:].strip()
    else:
        code = full.strip()
    for tag in ["<think>", "</think>", "<reasoning>", "</reasoning>"]:
        code = code.replace(tag, "")
    if "def get_signals" not in code:
        return None
    return code.strip()


def call_nvidia(prompt):
    print("[AGENT] Calling NVIDIA API...", flush=True)
    headers = {
        "Authorization": "Bearer " + NVIDIA_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "model": "deepseek-ai/deepseek-v4-pro",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.3
    }
    try:
        r = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=120
        )
        if r.status_code != 200:
            print("[AGENT] NVIDIA error: " + str(r.text), flush=True)
            return None
        full = r.json()["choices"][0]["message"]["content"]
        code = clean_code(full)
        if code is None:
            print("[AGENT] No valid function found", flush=True)
            return None
        print("[AGENT] Strategy ready", flush=True)
        return code
    except Exception as e:
        print("[AGENT] NVIDIA failed: " + str(e), flush=True)
        return None


def run_agent():
    if not NVIDIA_API_KEY:
        print("[ERROR] NVIDIA_API_KEY missing", flush=True)
        sys.exit(1)
    if not os.environ.get("COINDCX_API_KEY"):
        print("[ERROR] COINDCX_API_KEY missing", flush=True)
        sys.exit(1)
    if not os.environ.get("COINDCX_SECRET"):
        print("[ERROR] COINDCX_SECRET missing", flush=True)
        sys.exit(1)
    print("[AGENT] All keys found", flush=True)
    threading.Thread(target=start_api, daemon=True).start()
    strategy_code = None
    failed_tests = []
    loop_count = 0
    while True:
        try:
            loop_count += 1
            print("[AGENT] Loop " + str(loop_count), flush=True)
            all_data = get_top5_ohlcv()
            if not all_data:
                print("[AGENT] No data, waiting 10 mins", flush=True)
                time.sleep(600)
                continue
            market_summary = get_market_summary(all_data)
            if strategy_code is None or needs_regeneration():
                bump_strategy_version()
                good_coins = []
                attempts = 0
                while not good_coins and attempts < 5:
                    attempts += 1
                    print("[AGENT] Attempt " + str(attempts), flush=True)
                    if attempts == 1 or strategy_code is None:
                        prompt = build_prompt(market_summary)
                    else:
                        prompt = build_fix_prompt(market_summary, strategy_code, failed_tests)
                    strategy_code = call_nvidia(prompt)
                    if strategy_code is None:
                        print("[AGENT] Generation failed", flush=True)
                        time.sleep(10)
                        continue
                    results = run_backtest(strategy_code, all_data)
                    good_coins = is_strategy_good(results)
                    failed_tests = []
                    for coin, score in results.items():
                        if not score["passed"]:
                            if score["win_rate"] < 55.0:
                                failed_tests.append({
                                    "coin": coin,
                                    "test": "win_rate",
                                    "value": str(score["win_rate"]) + "%",
                                    "required": "above 55%"
                                })
                            if score["max_drawdown"] > 20.0:
                                failed_tests.append({
                                    "coin": coin,
                                    "test": "drawdown",
                                    "value": str(score["max_drawdown"]) + "%",
                                    "required": "below 20%"
                                })
                            if score["sharpe"] < 0.5:
                                failed_tests.append({
                                    "coin": coin,
                                    "test": "sharpe",
                                    "value": str(score["sharpe"]),
                                    "required": "above 0.5"
                                })
                    if not good_coins:
                        print("[AGENT] Issues: " + str(len(failed_tests)), flush=True)
                if not good_coins:
                    print("[AGENT] No good strategy, waiting 1 hour", flush=True)
                    time.sleep(3600)
                    continue
            else:
                results = run_backtest(strategy_code, all_data)
                good_coins = is_strategy_good(results)
            print("[AGENT] Trading: " + str(good_coins), flush=True)
            execute_strategy(strategy_code, all_data, good_coins)
            get_performance_summary()
            print("[AGENT] Sleeping 1 hour", flush=True)
            time.sleep(3600)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("[AGENT] Error: " + str(e), flush=True)
            time.sleep(900)


if __name__ == "__main__":
    run_agent()
