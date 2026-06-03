import requests
import hmac
import hashlib
import time
import os
import json

API_KEY = os.environ.get("COINDCX_API_KEY")
API_SECRET = os.environ.get("COINDCX_SECRET")

BASE_URL = "https://api.coindcx.com"

# maps Binance symbol → CoinDCX INR market
COIN_MAP = {
    'BTC': 'BTCINR',
    'ETH': 'ETHINR',
    'BNB': 'BNBINR',
    'SOL': 'SOLUSDT',
    'XRP': 'XRPINR'
}

TRADE_PERCENT = 0.30

def sign_request(body_dict):
    json_body = json.dumps(body_dict, separators=(',', ':'))
    signature = hmac.new(
        bytes(API_SECRET, 'utf-8'),
        msg=bytes(json_body, 'utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': API_KEY,
        'X-AUTH-SIGNATURE': signature
    }
    return json_body, headers

def get_balance():
    try:
        timestamp = int(round(time.time() * 1000))
        json_body, headers = sign_request({"timestamp": timestamp})
        response = requests.post(
            f"{BASE_URL}/exchange/v1/users/balances",
            data=json_body,
            headers=headers
        )
        balances = response.json()
        for b in balances:
            if b['currency'] == 'INR':
                inr = float(b['balance'])
                print(f"[TRADER] INR balance: Rs.{round(inr, 2)}")
                return inr
        print("[TRADER] INR balance not found")
        return 0
    except Exception as e:
        print(f"[TRADER] Balance fetch failed: {e}")
        return 0

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
            f"{BASE_URL}/exchange/v1/orders/create",
            data=json_body,
            headers=headers
        )
        result = response.json()
        print(f"[TRADER] {side.upper()} {coin_symbol} qty={quantity} → {result}")
        return result
    except Exception as e:
        print(f"[TRADER] Order failed {coin_symbol}: {e}")
        return None

def execute_strategy(strategy_code, all_data, good_coins):
    if not good_coins:
        print("[TRADER] No approved coins to trade")
        return {}

    local_env = {}
    exec(strategy_code, local_env)
    get_signals = local_env['get_signals']

    inr_balance = get_balance()
    if inr_balance < 100:
        print("[TRADER] Balance too low — need at least Rs.100")
        return {}

   trade_amount = inr_balance * TRADE_PERCENT
    if trade_amount < 110:
        trade_amount = 110
        print(f"[TRADER] 30% was below Rs.110 — using minimum Rs.110 per trade", flush=True)
    else:
        print(f"[TRADER] Using Rs.{round(trade_amount, 2)} per trade (30% of balance)", flush=True)

    for coin in good_coins:
        try:
            df = all_data[coin]
            signals = get_signals(df)
            last_signal = signals.iloc[-1]
            coin_symbol = COIN_MAP.get(coin)

            if not coin_symbol:
                print(f"[TRADER] No INR pair found for {coin} — skipping")
                continue

            current_price = df['close'].iloc[-1]

            if last_signal == 1:
                quantity = round(trade_amount / current_price, 6)
                print(f"[TRADER] BUY signal → {coin_symbol} qty={quantity}")
                order = place_order('buy', coin_symbol, quantity)
                results[coin] = {'action': 'buy', 'order': order}

            elif last_signal == -1:
                quantity = round(trade_amount / current_price, 6)
                print(f"[TRADER] SELL signal → {coin_symbol} qty={quantity}")
                order = place_order('sell', coin_symbol, quantity)
                results[coin] = {'action': 'sell', 'order': order}

            else:
                print(f"[TRADER] HOLD → {coin}")
                results[coin] = {'action': 'hold', 'order': None}

            time.sleep(1)

        except Exception as e:
            print(f"[TRADER] Error for {coin}: {e}")

    return results
