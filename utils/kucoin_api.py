import base64
import hashlib
import hmac
import time
import requests
import json

class KuCoinFutures:
    def __init__(self, api_key, api_secret, api_passphrase):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        self.base_url = "https://api-futures.kucoin.com"
    
    def _get_headers(self, method, endpoint, body=""):
        timestamp = int(time.time() * 1000)
        str_to_sign = str(timestamp) + method + endpoint + body
        signature = base64.b64encode(
            hmac.new(self.api_secret.encode(), str_to_sign.encode(), hashlib.sha256).digest()
        ).decode()
        passphrase = base64.b64encode(
            hmac.new(self.api_secret.encode(), self.api_passphrase.encode(), hashlib.sha256).digest()
        ).decode()
        return {
            "KC-API-KEY": self.api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(timestamp),
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }
    
    def get_balance(self):
        endpoint = "/api/v1/account-overview?currency=USDT"
        headers = self._get_headers("GET", endpoint)
        resp = requests.get(self.base_url + endpoint, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('code') == '200000':
                return float(data['data'].get('availableBalance', 0))
        return 0
    
    def get_position(self, symbol="XBTUSDTM"):
        endpoint = "/api/v1/positions"
        headers = self._get_headers("GET", endpoint)
        resp = requests.get(self.base_url + endpoint, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('code') == '200000':
                for pos in data.get('data', []):
                    if pos.get('symbol') == symbol:
                        qty = float(pos.get('currentQty', 0))
                        if qty != 0:
                            return {
                                "has_position": True,
                                "side": "long" if qty > 0 else "short",
                                "size": abs(qty),
                                "entry": float(pos.get('avgEntryPrice', 0)),
                                "current": float(pos.get('markPrice', 0)),
                                "pnl": float(pos.get('unrealisedPnl', 0))
                            }
        return {"has_position": False}
    
    def get_price(self, symbol="XBTUSDTM"):
        endpoint = f"/api/v1/ticker?symbol={symbol}"
        resp = requests.get(self.base_url + endpoint, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('code') == '200000':
                return float(data['data'].get('price', 0))
        return 0
    
    def place_order(self, side, size, symbol="XBTUSDTM", leverage=25, reduce_only=False):
        endpoint = "/api/v1/orders"
        order_body = {
            "clientOid": str(int(time.time() * 1000)),
            "side": side,
            "symbol": symbol,
            "type": "market",
            "size": int(size),
            "leverage": str(leverage),
            "marginMode": "CROSS"
        }
        if reduce_only:
            order_body["reduceOnly"] = True
        
        body = json.dumps(order_body)
        headers = self._get_headers("POST", endpoint, body)
        resp = requests.post(self.base_url + endpoint, headers=headers, data=body, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    
    def close_position(self, symbol="XBTUSDTM"):
        position = self.get_position(symbol)
        if not position['has_position']:
            return False
        
        side = "sell" if position['side'] == "long" else "buy"
        return self.place_order(side, position['size'], symbol, reduce_only=True)
