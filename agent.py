import sys
import os
import time
import requests
from data import get_top5_ohlcv, get_market_summary
from backtest import run_backtest, is_strategy_good
from trader import execute_strategy
from monitor import needs_regeneration, bump_strategy_version, get_performance_summary

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")

print("==================================================", flush=True)
print("TRADING AGENT STARTED", flush=True)
print("==================================================", flush=True)

def generate_strategy(market_summary, previous_feedback=None):
    feedback_text = ""
    if previous_feedback:
        feedback_text = "Previous strategy failed: " + previous_feedback + " Make a different approach."

    prompt = """You are an expert algorithmic trading strategy developer.

Current market data:
""" + market_summary + """
""" + feedback_text + """

Write a Python function called get_signals(df) that:
- Takes a pandas DataFrame with columns: open, high, low, close, volume
- Returns a pandas Series of signals: 1 = buy, -1 = sell, 0 = hold
- Uses technical indicators like EMA, RSI, Bollinger Bands
- Is conservative — only signals when very confident
- Use only pandas and numpy
- Return ONLY the raw Python function, no exp
