import requests
import hmac
import hashlib
import time
import os
import json
import re
import threading

API_KEY = os.environ.get("COINDCX_API_KEY")
API_SECRET = os.environ.get("COINDCX_SECRET")
TRADE_MODE = os.environ.get("TRADE_MODE", "spot").lower()

BASE_URL = "https://api.coindcx.com"

COIN_MAP = {
    "BTC": "BTCINR",
    "ETH": "ETHINR",
    "BNB": "BNBINR",
    "SOL": "SOLUSDT",
    "XRP": "XRPINR"
}

FUTURES_PAIR_MAP = {
    "BTC": "B-BTC_USDT",
    "ETH": "B-ETH_USDT",
    "BNB": "B-BNB_USDT",
    "SOL": "B-SOL_USDT",
    "XRP": "B-XRP_USDT"
}

TRADE_PERCENT = 0.10
MIN_TRADE = 110
MAX_TRADE = 500
FUTURES_LEVERAGE = 3
INTERVALS = ["5m", "15m", "30m", "1h"]

POSITIONS_FILE = "positions.json"
positions_lock = threading.Lock()
_balance_cache = {"value": None, "time": 0}
_balance_cache_lock = threading.Lock()
_futures_instruments_cache = None
_futures_instruments_time = 0

def sign_request(body_dict):
    if not API_KEY or not API_SECRET:
        raise ValueError("CoinDCX API keys not configured")
    json_body = json.dumps(body_dict, separators=(",", ":"))
    signature = hmac.new(
        bytes(API_SECRET, "utf-8"),
        msg=bytes(json_body, "utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-AUTH-APIKEY": API_KEY,
        "X-AUTH-SIGNATURE": signature
    }
    return json_body, headers

def load_positions():
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_positions(positions):
    with open(POSITIONS_FILE, "w") as f:
        json.dump(positions, f, indent=2)

def get_balance():
    now = time.time()
    with _balance_cache_lock:
        if _balance_cache["value"] is not None and now - _balance_cache["time"] < 60:
            return _balance_cache["value"]
    try:
        timestamp = int(round(time.time() * 1000))
        json_body, headers = sign_request({"timestamp": timestamp})
        response = requests.post(
            BASE_URL + "/exchange/v1/users/balances",
            data=json_body, headers=headers, timeout=10
        )
        resp = response.json()
        if isinstance(resp, dict):
            balances = resp.get("data", resp.get("balances", []))
        else:
            balances = resp
        for b in balances:
            if not isinstance(b, dict):
                continue
            if b.get("currency") == "INR":
                inr = float(b.get("balance", 0))
                print("[TRADER] INR balance: Rs." + str(round(inr, 2)), flush=True)
                with _balance_cache_lock:
                    _balance_cache["value"] = inr
                    _balance_cache["time"] = now
                return inr
        print("[TRADER] No INR balance found: " + json.dumps(balances)[:200], flush=True)
        with _balance_cache_lock:
            _balance_cache["value"] = 0
            _balance_cache["time"] = now
        return 0
    except Exception as e:
        print("[TRADER] Balance fetch failed: " + str(e), flush=True)
        with _balance_cache_lock:
            _balance_cache["value"] = 0
            _balance_cache["time"] = now
        return 0

def get_futures_balance():
    try:
        timestamp = int(round(time.time() * 1000))
        json_body, headers = sign_request({"timestamp": timestamp})
        response = requests.post(
            BASE_URL + "/exchange/v1/users/balances",
            data=json_body, headers=headers, timeout=10
        )
        resp = response.json()
        if isinstance(resp, dict):
            balances = resp.get("data", resp.get("balances", []))
        else:
            balances = resp
        usdt = 0
        for b in balances:
            if not isinstance(b, dict):
                continue
            if b.get("currency") == "USDT":
                usdt = float(b.get("balance", 0))
        print("[TRADER] Futures USDT balance: " + str(round(usdt, 2)), flush=True)
        return usdt
    except Exception as e:
        print("[TRADER] Futures balance fetch failed: " + str(e), flush=True)
        return 0

def check_futures_instrument(pair):
    global _futures_instruments_cache, _futures_instruments_time
    now = time.time()
    if _futures_instruments_cache and now - _futures_instruments_time < 300:
        return pair in _futures_instruments_cache
    try:
        resp = requests.get(
            BASE_URL + "/exchange/v1/derivatives/futures/data/instrument?pair=" + pair,
            timeout=10
        )
        data = resp.json()
        instr = data.get("instrument", {})
        active = instr.get("status") == "active"
        if active:
            if _futures_instruments_cache is None:
                _futures_instruments_cache = set()
            _futures_instruments_cache.add(pair)
            _futures_instruments_time = now
        return active
    except:
        return False

def place_order(side, coin_symbol, quantity):
    try:
        timestamp = int(round(time.time() * 1000))
        body = {
            "side": side,
            "order_type": "market_order",
            "market": coin_symbol,
            "quantity": quantity,
            "timestamp": timestamp
        }
        json_body, headers = sign_request(body)
        response = requests.post(
            BASE_URL + "/exchange/v1/orders/create",
            data=json_body, headers=headers
        )
        result = response.json()
        print("[TRADER] SPOT " + side.upper() + " " + coin_symbol + " qty=" + str(quantity) + " result=" + str(result)[:200], flush=True)
        return result
    except Exception as e:
        print("[TRADER] Spot order failed " + coin_symbol + ": " + str(e), flush=True)
        return None

def place_futures_order(side, pair, quantity):
    try:
        timestamp = int(round(time.time() * 1000))
        body = {
            "timestamp": timestamp,
            "side": side,
            "pair": pair,
            "order_type": "market",
            "total_quantity": quantity,
            "leverage": FUTURES_LEVERAGE,
            "price": 0
        }
        json_body, headers = sign_request(body)
        response = requests.post(
            BASE_URL + "/exchange/v1/derivatives/futures/orders/create",
            data=json_body, headers=headers
        )
        result = response.json()
        print("[TRADER] FUTURES " + side.upper() + " " + pair + " qty=" + str(quantity) + " lev=" + str(FUTURES_LEVERAGE) + "x result=" + str(result)[:200], flush=True)
        return result
    except Exception as e:
        print("[TRADER] Futures order failed " + pair + ": " + str(e), flush=True)
        return None

def parse_sl_tp(strategy_code):
    sl_pct = 3.0
    tp_pct = 6.0
    sl_match = re.search(r'SL_PCT\s*=\s*([\d.]+)', strategy_code)
    tp_match = re.search(r'TP_PCT\s*=\s*([\d.]+)', strategy_code)
    if sl_match:
        sl_pct = float(sl_match.group(1))
    if tp_match:
        tp_pct = float(tp_match.group(1))
    print("[TRADER] SL=" + str(sl_pct) + "% TP=" + str(tp_pct) + "%", flush=True)
    return sl_pct, tp_pct

def _pick_price(all_data, coin):
    for tf in ["1h", "30m", "15m", "5m"]:
        if coin in all_data and tf in all_data[coin]:
            return float(all_data[coin][tf]["close"].iloc[-1])
    return 0

def check_and_close_positions(all_data):
    positions = load_positions()
    if not positions:
        return
    to_remove = []
    for coin, pos in positions.items():
        try:
            current_price = _pick_price(all_data, coin)
            if current_price == 0:
                continue
            entry = pos["entry_price"]
            sl_pct = pos["sl_pct"]
            tp_pct = pos["tp_pct"]
            side = pos.get("side", "long")
            if side == "short":
                pct_change = (entry - current_price) / entry * 100.0
            else:
                pct_change = (current_price - entry) / entry * 100.0
            if pct_change <= -sl_pct:
                print("[TRADER] SL HIT " + coin + " (" + side + " " + str(round(pct_change, 2)) + "%)", flush=True)
                if TRADE_MODE == "futures":
                    close_side = "buy" if side == "short" else "sell"
                    place_futures_order(close_side, FUTURES_PAIR_MAP[coin], pos["quantity"])
                else:
                    coin_symbol = COIN_MAP.get(coin)
                    if coin_symbol:
                        place_order("sell", coin_symbol, pos["quantity"])
                to_remove.append(coin)
                from monitor import record_trade
                record_trade(coin, "sell", entry, current_price, pos["quantity"])
            elif pct_change >= tp_pct:
                print("[TRADER] TP HIT " + coin + " (" + side + " " + str(round(pct_change, 2)) + "%)", flush=True)
                if TRADE_MODE == "futures":
                    close_side = "buy" if side == "short" else "sell"
                    place_futures_order(close_side, FUTURES_PAIR_MAP[coin], pos["quantity"])
                else:
                    coin_symbol = COIN_MAP.get(coin)
                    if coin_symbol:
                        place_order("sell", coin_symbol, pos["quantity"])
                to_remove.append(coin)
                from monitor import record_trade
                record_trade(coin, "sell", entry, current_price, pos["quantity"])
        except Exception as e:
            print("[TRADER] Position check error " + coin + ": " + str(e), flush=True)
    if to_remove:
        with positions_lock:
            positions = load_positions()
            for c in to_remove:
                positions.pop(c, None)
            save_positions(positions)

def execute_strategy(strategy_code, all_data, good_coins):
    check_and_close_positions(all_data)
    if not good_coins:
        print("[TRADER] No approved coins to trade", flush=True)
        return {}
    local_env = {}
    exec(strategy_code, local_env)
    get_signals = local_env["get_signals"]
    sl_pct, tp_pct = parse_sl_tp(strategy_code)

    if TRADE_MODE == "futures":
        usdt = get_futures_balance()
        if usdt < 5:
            print("[TRADER] Futures balance too low - need at least 5 USDT, have " + str(round(usdt, 2)), flush=True)
            return {}
        trade_amount = usdt * TRADE_PERCENT
        if trade_amount > 50:
            trade_amount = 50
        if trade_amount < 5:
            trade_amount = 5
        print("[TRADER] Futures trade amount: " + str(round(trade_amount, 2)) + " USDT", flush=True)
    else:
        inr_balance = get_balance()
        if inr_balance < MIN_TRADE:
            print("[TRADER] Balance too low - need at least Rs." + str(MIN_TRADE), flush=True)
            return {}
        trade_amount = inr_balance * TRADE_PERCENT
        if trade_amount < MIN_TRADE:
            trade_amount = MIN_TRADE
        if trade_amount > MAX_TRADE:
            trade_amount = MAX_TRADE

    results = {}
    for coin in good_coins:
        try:
            coin_data = all_data.get(coin, {})
            if not coin_data:
                continue
            available_tfs = [tf for tf in INTERVALS if tf in coin_data]
            if not available_tfs:
                continue
            best_signal = 0
            signal_detail = []
            for tf in available_tfs:
                df = coin_data[tf]
                sig = int(get_signals(df.copy()).iloc[-1])
                price = float(df["close"].iloc[-1])
                signal_detail.append(tf + "=" + str(sig) + "@" + str(round(price, 2)))
                if sig != 0:
                    best_signal = sig
            current_price = _pick_price(all_data, coin)
            positions = load_positions()
            pair = FUTURES_PAIR_MAP[coin] if TRADE_MODE == "futures" else COIN_MAP[coin]
            print("[TRADER] " + coin + " sigs=[" + ", ".join(signal_detail) + "] pos=" + str(coin in positions), flush=True)

            if TRADE_MODE == "futures":
                if best_signal == 1:
                    if coin in positions and positions[coin].get("side") == "short":
                        print("[TRADER] CLOSE SHORT " + coin + " (signal=1)", flush=True)
                        order = place_futures_order("buy", pair, positions[coin]["quantity"])
                        if order and order.get("code") != "error":
                            from monitor import record_trade
                            record_trade(coin, "buy", positions[coin]["entry_price"], current_price, positions[coin]["quantity"])
                            with positions_lock:
                                p = load_positions(); p.pop(coin, None); save_positions(p)
                            print("[TRADER] Short closed for " + coin, flush=True)
                        results[coin] = {"action": "close_short", "order": order}
                    elif coin in positions and positions[coin].get("side") == "long":
                        print("[TRADER] Already long " + coin + " - holding", flush=True)
                        results[coin] = {"action": "hold"}
                    else:
                        quantity = round(trade_amount / current_price, 6)
                        print("[TRADER] LONG " + coin + " qty=" + str(quantity) + " at " + str(round(current_price, 2)), flush=True)
                        order = place_futures_order("buy", pair, quantity)
                        if order and order.get("code") != "error":
                            with positions_lock:
                                p = load_positions()
                                p[coin] = {"entry_price": current_price, "quantity": quantity, "sl_pct": sl_pct, "tp_pct": tp_pct, "entry_time": time.time(), "side": "long"}
                                save_positions(p)
                            print("[TRADER] LONG opened for " + coin, flush=True)
                        results[coin] = {"action": "long", "order": order, "price": current_price, "quantity": quantity}
                elif best_signal == -1:
                    if coin in positions and positions[coin].get("side") == "long":
                        print("[TRADER] CLOSE LONG " + coin + " (signal=-1)", flush=True)
                        order = place_futures_order("sell", pair, positions[coin]["quantity"])
                        if order and order.get("code") != "error":
                            from monitor import record_trade
                            record_trade(coin, "sell", positions[coin]["entry_price"], current_price, positions[coin]["quantity"])
                            with positions_lock:
                                p = load_positions(); p.pop(coin, None); save_positions(p)
                            print("[TRADER] Long closed for " + coin, flush=True)
                        results[coin] = {"action": "close_long", "order": order}
                    elif coin in positions and positions[coin].get("side") == "short":
                        print("[TRADER] Already short " + coin + " - holding", flush=True)
                        results[coin] = {"action": "hold"}
                    else:
                        quantity = round(trade_amount / current_price, 6)
                        print("[TRADER] SHORT " + coin + " qty=" + str(quantity) + " at " + str(round(current_price, 2)), flush=True)
                        order = place_futures_order("sell", pair, quantity)
                        if order and order.get("code") != "error":
                            with positions_lock:
                                p = load_positions()
                                p[coin] = {"entry_price": current_price, "quantity": quantity, "sl_pct": sl_pct, "tp_pct": tp_pct, "entry_time": time.time(), "side": "short"}
                                save_positions(p)
                            print("[TRADER] SHORT opened for " + coin, flush=True)
                        results[coin] = {"action": "short", "order": order, "price": current_price, "quantity": quantity}
                else:
                    results[coin] = {"action": "hold", "order": None}
            else:
                if best_signal == 1 and coin not in positions:
                    quantity = round(trade_amount / current_price, 6)
                    print("[TRADER] BUY " + coin + " qty=" + str(quantity) + " at Rs." + str(round(current_price, 2)), flush=True)
                    order = place_order("buy", pair, quantity)
                    if order and "id" in order:
                        with positions_lock:
                            p = load_positions()
                            p[coin] = {"entry_price": current_price, "quantity": quantity, "sl_pct": sl_pct, "tp_pct": tp_pct, "entry_time": time.time(), "side": "long"}
                            save_positions(p)
                        print("[TRADER] Position opened for " + coin, flush=True)
                    results[coin] = {"action": "buy", "order": order, "price": current_price, "quantity": quantity}
                elif best_signal == -1 and coin in positions:
                    print("[TRADER] SELL " + coin + " (signal=-1)", flush=True)
                    order = place_order("sell", pair, positions[coin]["quantity"])
                    if order and "id" in order:
                        from monitor import record_trade
                        record_trade(coin, "sell", positions[coin]["entry_price"], current_price, positions[coin]["quantity"])
                        with positions_lock:
                            p = load_positions(); p.pop(coin, None); save_positions(p)
                        print("[TRADER] Position closed for " + coin, flush=True)
                    results[coin] = {"action": "sell", "order": order}
                elif best_signal == -1 and coin not in positions:
                    print("[TRADER] SHORT signal for " + coin + " - set TRADE_MODE=futures to short", flush=True)
                    results[coin] = {"action": "short_signal_no_pos"}
                else:
                    results[coin] = {"action": "hold", "order": None}
            time.sleep(1)
        except Exception as e:
            print("[TRADER] Error for " + coin + ": " + str(e), flush=True)
    return results
