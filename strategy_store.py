import json
import os

STORE_FILE = "strategy_store.json"

def save_strategy(strategy_code, good_coins):
    data = {
        "strategy_code": strategy_code,
        "good_coins": good_coins
    }
    with open(STORE_FILE, "w") as f:
        json.dump(data, f)
    print("[STORE] Strategy saved for coins: " + str(good_coins), flush=True)

def load_strategy():
    if not os.path.exists(STORE_FILE):
        print("[STORE] No saved strategy found", flush=True)
        return None, []
    try:
        with open(STORE_FILE, "r") as f:
            data = json.load(f)
        print("[STORE] Loaded strategy for coins: " + str(data["good_coins"]), flush=True)
        return data["strategy_code"], data["good_coins"]
    except Exception as e:
        print("[STORE] Load failed: " + str(e), flush=True)
        return None, []

def clear_strategy():
    if os.path.exists(STORE_FILE):
        os.remove(STORE_FILE)
        print("[STORE] Strategy cleared", flush=True)
