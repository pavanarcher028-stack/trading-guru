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
    'BTC': 'BTCINR',
    'ETH': 'ETHINR',
    'BNB': 'BNBINR',
    'SOL': 'SOLUSDT',
    'XRP': 'XRPINR'
}

TRADE_PERCENT = 0.30
MIN_TRADE = 110

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
            if b['currency'] == 'IN
