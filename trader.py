import requests
import hmac
import hashlib
import time
import os
import json

API_KEY = os.environ.get("COINDCX_API_KEY")
API_SECRET = os.environ.get("COINDCX_SECRET")

BASE_URL = "https://api.coindcx.com"

COIN_MAP = {
    'BTC/USDT': 'BTCINR',
    'ETH/USDT': 'ETHINR',
    'XRP/USDT': 'XRPINR',
    'SOL/USDT': 'SOLINR',
    'DOGE/USDT': 'DOGEINR'
}

TRADE_PERCENT = 0.30

def get_balance():
    try:
        timestamp = int(round(time.time() * 1000))
        body = {"timestamp": timestamp}
        json_body = json.dumps(body, separators=(',', ':'))
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

        response = requests.post(
            f"{BASE_URL}/exchange/v1/users/balances",
            data=json_body,
            headers=headers
        )
        balances = response.json()
        for b in balances:
            if b['currency'] == 'INR':
                inr = float(b['balance'])
                print(f"Available balance: Rs.{round(inr, 2)}")
                return inr
        return 0
    except Exception as e:
        print(f"Balance fetch failed: {e}")
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
        json_body = json.dumps(body, separators=(',', ':'))
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

        response = requests.post(
            f"{BASE_URL}/exchange/v1/orders/create",
            data=json_body,
            headers=headers
        )
        result = response.json()
        print(f"{side.upper()} order placed for {coin_symbol}: {result}")
        return result
    except Exception as e:
        print(f"Order failed for {coin_symbol}: {e}")
        return None

def execute_strategy(strategy_code, all_data, good_coins):
    if not good_coins:
        print("No approved coins to trade")
        return {}

    local_env = {}
    exec(strategy_code, local_env)
    get_signals = local_env['get_signals']

    inr_balance = get_balance()
    if inr_balance < 100:
        print("Balance too low to trade")
        return {}

    trade_amount = inr_balance * TRADE_PERCENT
    results = {}

    for coin in good_coins:
        try:
            df = all_data[coin]
            signals = get_signals(df)
            last_signal = signals.iloc[-1]
            coin_symbol = COIN_MAP.get(coin, None)

            if not coin_symbol:
                continue

            current_price = df['close'].iloc[-1]

            if last_signal == 1:
                quantity = round(trade_amount / current_price, 6)
                print(f"Signal: BUY {coin_symbol} qty={quantity}")
                order = place_order('buy', coin_symbol, quantity)
                results[coin] = {'action': 'buy', 'order': order}

            elif last_signal == -1:
                quantity = round(trade_amount / current_price, 6)
                print(f"Signal: SELL {coin_symbol} qty={quantity}")
                order = place_order('sell', coin_symbol, quantity)
                results[coin] = {'action': 'sell', 'order': order}

            else:
                print(f"Signal: HOLD {coin}")
                results[coin] = {'action': 'hold', 'order': None}

            time.sleep(1)

        except Exception as e:
            print(f"Trade execution failed for {coin}: {e}")

    return results
