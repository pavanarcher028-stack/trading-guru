import os
import requests
import time
import json


def improve_strategy_with_google_ai(strategy_code, failed_metrics, coin, item=None):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[GOOGLE_AI] GEMINI_API_KEY not set", flush=True)
        return None

    sharpe = str(item.get("sharpe", "unknown")) if item else "unknown"
    win_rate = str(item.get("win_rate", "unknown")) if item else "unknown"
    max_drawdown = str(item.get("max_drawdown", "unknown")) if item else "unknown"
    trades = str(item.get("trades", "unknown")) if item else "unknown"

    failed_text = ""
    for metric in failed_metrics:
        if metric == "sharpe":
            failed_text += "- Sharpe ratio is " + sharpe + " but must be above 0.5. Fix: normalize signals by rolling volatility, only take high confidence signals\n"
        elif metric == "win_rate":
            failed_text += "- Win rate is " + win_rate + "% but must be above 55%. Fix: require 3 confluence conditions, add volume confirmation\n"
        elif metric == "max_drawdown":
            failed_text += "- Drawdown is " + max_drawdown + "% but must be below 15%. Fix: add 100 EMA trend filter, only buy above it\n"
        elif metric == "trades_count":
            failed_text += "- Only " + trades + " trades but need at least 5. Fix: use shorter rolling windows, lower thresholds slightly\n"

    passed_text = ""
    if item:
        try:
            if float(sharpe) >= 0.5:
                passed_text += "  Sharpe: " + sharpe + " PASSED - do not change\n"
            if float(win_rate) >= 55.0:
                passed_text += "  Win rate: " + win_rate + "% PASSED - do not change\n"
            if float(max_drawdown) <= 15.0:
                passed_text += "  Drawdown: " + max_drawdown + "% PASSED - do not change\n"
            if int(trades) >= 5:
                passed_text += "  Trades: " + trades + " PASSED - do not change\n"
        except:
            pass

    prompt = "You are the world's most advanced quantitative trading AI.\n"
    prompt += "You have studied every paper in the Journal of Finance and Quantitative Finance.\n"
    prompt += "You have built strategies for Renaissance Technologies, Two Sigma, and Citadel.\n"
    prompt += "\n"
    prompt += "YOUR MISSION: Fix this failing trading strategy for coin " + coin + " on 1-hour crypto candles.\n"
    prompt += "\n"
    prompt += "THE BACKTEST SYSTEM EXACT RULES:\n"
    prompt += "- Data: 1000 hourly candles of open, high, low, close, volume\n"
    prompt += "- The strategy defines its own SL_PCT and TP_PCT inside the function\n"
    prompt += "- Example: SL_PCT = 2.0 means exit if price drops 2 percent from entry\n"
    prompt += "- Example: TP_PCT = 5.0 means exit if price rises 5 percent from entry\n"
    prompt += "- Time stop: exits after 48 candles maximum\n"
    prompt += "\n"
    prompt += "PASS THRESHOLDS YOUR STRATEGY MUST HIT:\n"
    prompt += "  Sharpe ratio: above 0.5\n"
    prompt += "  Win rate: above 55 percent\n"
    prompt += "  Max drawdown: below 15 percent\n"
    prompt += "  Minimum trades: at least 5 over 1000 candles\n"
    prompt += "\n"
    prompt += "CURRENT STRATEGY SCORES:\n"
    prompt += "  Sharpe: " + sharpe + " (target above 0.5)\n"
    prompt += "  Win rate: " + win_rate + "% (target above 55%)\n"
    prompt += "  Drawdown: " + max_drawdown + "% (target below 15%)\n"
    prompt += "  Trades: " + trades + " (target at least 5)\n"
    prompt += "\n"
    prompt += "THESE METRICS ARE ALREADY PASSING - DO NOT CHANGE THEM:\n"
    prompt += passed_text if passed_text else "  None yet\n"
    prompt += "\n"
    prompt += "ONLY THESE ARE FAILING - FIX ONLY THESE:\n"
    prompt += failed_text
    prompt += "\n"
    prompt += "CURRENT WORKING STRATEGY CODE:\n"
    prompt += strategy_code + "\n"
    prompt += "\n"
    prompt += "ADVANCED QUANT TECHNIQUES TO APPLY:\n"
    prompt += "- For low Sharpe: divide signal by rolling_std(20) to normalize, filter out noise\n"
    prompt += "- For low win rate: add volume above 20 period average + momentum confirmation\n"
    prompt += "- For high drawdown: add EMA 100 trend filter, only buy when price above EMA 100\n"
    prompt += "- For few trades: shorten rolling windows to 10-20 periods, lower z-score thresholds\n"
    prompt += "- Choose SL_PCT and TP_PCT that maximize Sharpe for this strategy type\n"
    prompt += "- For mean reversion: SL_PCT = 1.5 to 2.5 and TP_PCT = 2.0 to 4.0\n"
    prompt += "- For momentum: SL_PCT = 3.0 to 5.0 and TP_PCT = 6.0 to 12.0\n"
    prompt += "\n"
    prompt += "STRICT RULES:\n"
    prompt += "1. Do NOT change any logic that is already passing its threshold\n"
    prompt += "2. ONLY fix the failing metric\n"
    prompt += "3. Use ONLY pandas and numpy\n"
    prompt += "4. First two lines inside function must be: import pandas as pd and import numpy as np\n"
    prompt += "5. Define SL_PCT and TP_PCT inside the function\n"
    prompt += "6. Return pandas Series: 1=buy -1=sell 0=hold\n"
    prompt += "7. Generate at least 10 signals over 1000 candles\n"
    prompt += "\n"
    prompt += "Return ONLY the complete get_signals(df) function. No markdown. No explanation.\n"

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + api_key
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    def parse_code(text):
        if "```python" in text:
            code = text.split("```python")[1].split("```")[0].strip()
        elif "```" in text:
            code = text.split("```")[1].split("```")[0].strip()
        elif "def get_signals" in text:
            code = text[text.index("def get_signals"):].strip()
        else:
            code = text.strip()
        if "def get_signals" in code:
            return code
        return None

    try:
        r = requests.post(url, json=body, timeout=60)
        if r.status_code == 200:
            full = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            code = parse_code(full)
            if code:
                print("[GOOGLE_AI] Strategy improved for " + coin + " fixing: " + str(failed_metrics), flush=True)
                return code
            print("[GOOGLE_AI] No valid function returned", flush=True)
            return None
        elif r.status_code == 429:
            print("[GOOGLE_AI] Rate limited - waiting 60 seconds and retrying...", flush=True)
            time.sleep(60)
            r = requests.post(url, json=body, timeout=60)
            if r.status_code == 200:
                full = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                code = parse_code(full)
                if code:
                    print("[GOOGLE_AI] Strategy improved on retry for " + coin, flush=True)
                    return code
            print("[GOOGLE_AI] Rate limited even after retry - skipping", flush=True)
            return None
        else:
            print("[GOOGLE_AI] Error: " + str(r.status_code), flush=True)
            return None
    except Exception as e:
        print("[GOOGLE_AI] Failed: " + str(e), flush=True)
        return None


def validate_with_nvidia(strategy_code, coin):
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"valid": True, "errors": [], "fixed_code": ""}

    prompt = "You are the world's best hedge fund code reviewer and quantitative developer.\n"
    prompt += "You review trading strategy code like a senior quant at Renaissance Technologies.\n"
    prompt += "\n"
    prompt += "Review this Python trading strategy function:\n"
    prompt += strategy_code + "\n"
    prompt += "\n"
    prompt += "Check for:\n"
    prompt += "1. Syntax errors that will crash Python\n"
    prompt += "2. Logic errors that produce wrong signals\n"
    prompt += "3. Pandas or numpy mistakes\n"
    prompt += "4. Missing imports inside the function\n"
    prompt += "5. Division by zero risks\n"
    prompt += "6. NaN handling issues\n"
    prompt += "\n"
    prompt += "Reply ONLY in this exact JSON format with no other text:\n"
    prompt += "{\"valid\": true, \"errors\": [], \"fixed_code\": \"\"}\n"
    prompt += "If errors found: set valid to false, list errors, put fixed code in fixed_code.\n"
    prompt += "If no errors: set valid to true, errors to empty list, fixed_code to empty string.\n"

    try:
        r = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-ai/deepseek-v4-pro",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1500,
                "temperature": 0.1
            },
            timeout=60
        )
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"]["content"]
            try:
                start = content.find("{")
                end = content.rfind("}") + 1
                result = json.loads(content[start:end])
                if result.get("errors"):
                    print("[NVIDIA] Errors in " + coin + ": " + str(result.get("errors")), flush=True)
                if result.get("fixed_code") and len(result.get("fixed_code", "")) > 10:
                    print("[NVIDIA] Auto-fixed code for " + coin, flush=True)
                    result["auto_fixed"] = True
                return result
            except:
                return {"valid": True, "errors": [], "fixed_code": ""}
        return {"valid": True, "errors": [], "fixed_code": ""}
    except Exception as e:
        print("[NVIDIA] Failed: " + str(e), flush=True)
        return {"valid": True, "errors": [], "fixed_code": ""}


def batch_improve_and_validate_strategies(partial_fails, strategy_code):
    improved = {}
    for item in partial_fails:
        coin = item["coin"]
        failed_metrics = item["failed_metrics"]
        if len(failed_metrics) != 1:
            print("[PIPELINE] " + coin + " has " + str(len(failed_metrics)) + " failures - only fixing when exactly 1 fails skipping", flush=True)
            continue
        print("[PIPELINE] " + coin + " fixing only: " + str(failed_metrics), flush=True)
        time.sleep(90)
        new_code = improve_strategy_with_google_ai(strategy_code, failed_metrics, coin, item)
        if not new_code:
            print("[PIPELINE] Could not improve " + coin, flush=True)
            continue
        validation = validate_with_nvidia(new_code, coin)
        if not validation.get("valid", True):
            if validation.get("fixed_code") and len(validation.get("fixed_code", "")) > 10:
                print("[PIPELINE] NVIDIA auto-fixed errors for " + coin, flush=True)
                new_code = validation["fixed_code"]
            else:
                print("[PIPELINE] " + coin + " has unfixable errors skipping", flush=True)
                continue
        improved[coin] = new_code
        print("[PIPELINE] " + coin + " improved validated and ready for backtest", flush=True)
    return improved


def generate_html_report(partial_fails, improved_strategies):
    return None
