import requests
from datetime import datetime

class ExchangeAgent:
    def __init__(self):
        self.name = "Exchange Analyst"
    
    async def analyze(self):
        """Analisis data dari exchange (harga spot + funding rate futures + order book)"""
        
        # Harga spot
        coinbase = await self._get_coinbase()
        kraken = await self._get_kraken()
        binance_spot = await self._get_binance_spot()
        
        # Order book depth dari semua exchange
        order_books = await self._get_all_order_books()
        
        # Funding rates
        funding_rates = await self._get_all_funding_rates()
        
        result = self._analyze_flow(coinbase, kraken, binance_spot, order_books, funding_rates)
        
        return {
            "agent": self.name,
            "signal": result["signal"],
            "confidence": result["confidence"],
            "coinbase": coinbase,
            "kraken": kraken,
            "binance_spot": binance_spot,
            "order_books": order_books,
            "funding_rates": funding_rates,
            "reason": result["reason"],
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_coinbase(self):
        try:
            resp = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=5)
            if resp.status_code == 200:
                price = float(resp.json()['data']['amount'])
                return {"price": price, "status": "OK"}
        except:
            pass
        return {"price": 0, "status": "ERROR"}
    
    async def _get_kraken(self):
        try:
            resp = requests.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD", timeout=5)
            if resp.status_code == 200:
                data = resp.json()['result']['XXBTZUSD']
                return {"bid": float(data['b'][0]), "ask": float(data['a'][0]), "last": float(data['c'][0]), "status": "OK"}
        except:
            pass
        return {"last": 0, "status": "ERROR"}
    
    async def _get_binance_spot(self):
        try:
            resp = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return {"price": float(data['price']), "status": "OK"}
        except:
            pass
        return {"status": "ERROR"}
    
    async def _get_all_order_books(self):
        """Ambil order book dari Binance (gratis, no auth)"""
        results = {}
        
        # Binance Order Book
        try:
            url = "https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=10"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                bids = data.get('bids', [])
                asks = data.get('asks', [])
                best_bid = float(bids[0][0]) if bids else 0
                best_ask = float(asks[0][0]) if asks else 0
                spread = best_ask - best_bid
                spread_pct = (spread / best_bid) * 100 if best_bid > 0 else 0
                
                # Hitung support/resistance dari order book
                bid_volume = sum(float(b[1]) for b in bids[:5])
                ask_volume = sum(float(a[1]) for a in asks[:5])
                bid_ask_ratio = bid_volume / ask_volume if ask_volume > 0 else 1
                
                results['binance'] = {
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "spread": spread,
                    "spread_pct": round(spread_pct, 3),
                    "bid_ask_ratio": round(bid_ask_ratio, 2),
                    "status": "OK"
                }
            else:
                results['binance'] = {"status": "ERROR", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            results['binance'] = {"status": "ERROR", "error": str(e)}
        
        # Bybit Order Book
        try:
            url = "https://api.bybit.com/v5/market/orderbook?category=linear&symbol=BTCUSDT&limit=10"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('retCode') == 0:
                    result = data.get('result', {})
                    bids = result.get('b', [])
                    asks = result.get('a', [])
                    best_bid = float(bids[0][0]) if bids else 0
                    best_ask = float(asks[0][0]) if asks else 0
                    spread = best_ask - best_bid
                    spread_pct = (spread / best_bid) * 100 if best_bid > 0 else 0
                    
                    results['bybit'] = {
                        "best_bid": best_bid,
                        "best_ask": best_ask,
                        "spread": spread,
                        "spread_pct": round(spread_pct, 3),
                        "status": "OK"
                    }
            else:
                results['bybit'] = {"status": "ERROR", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            results['bybit'] = {"status": "ERROR", "error": str(e)}
        
        # OKX Order Book
        try:
            url = "https://www.okx.com/api/v5/market/books?instId=BTC-USDT&sz=10"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == '0':
                    bids = data.get('data', [{}])[0].get('bids', [])
                    asks = data.get('data', [{}])[0].get('asks', [])
                    best_bid = float(bids[0][0]) if bids else 0
                    best_ask = float(asks[0][0]) if asks else 0
                    spread = best_ask - best_bid
                    spread_pct = (spread / best_bid) * 100 if best_bid > 0 else 0
                    
                    results['okx'] = {
                        "best_bid": best_bid,
                        "best_ask": best_ask,
                        "spread": spread,
                        "spread_pct": round(spread_pct, 3),
                        "status": "OK"
                    }
            else:
                results['okx'] = {"status": "ERROR", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            results['okx'] = {"status": "ERROR", "error": str(e)}
        

        # Hyperliquid
        try:
            current_time = int(__import__("time").time() * 1000)
            seven_days_ago = current_time - (7 * 24 * 60 * 60 * 1000)
            resp = requests.post(
                "https://api.hyperliquid.xyz/info",
                headers={"Content-Type": "application/json"},
                json={"type": "fundingHistory", "coin": "BTC", "startTime": seven_days_ago},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    rate = float(data[0].get('fundingRate', 0))
                    results['hyperliquid'] = {"rate": rate, "signal": "SELL" if rate > 0.01 else "BUY" if rate < -0.005 else "HOLD"}
        except:
            pass
        

        return results
    
    async def _get_all_funding_rates(self):
        """Ambil funding rate dari exchange yang support free API"""
        results = {}
        
        # Binance Futures
        try:
            url = "https://dapi.binance.com/dapi/v1/fundingRate?symbol=BTCUSD_PERP&limit=1"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200 and resp.json():
                rate = float(resp.json()[0]['fundingRate'])
                results['binance'] = {"rate": rate, "signal": "SELL" if rate > 0.01 else "BUY" if rate < -0.005 else "HOLD"}
        except: pass
        
        # Bybit Futures
        try:
            url = "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200 and resp.json().get('retCode') == 0:
                rate = float(resp.json()['result']['list'][0]['fundingRate'])
                results['bybit'] = {"rate": rate, "signal": "SELL" if rate > 0.01 else "BUY" if rate < -0.005 else "HOLD"}
        except: pass
        
        # OKX Futures
        try:
            url = "https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USD-SWAP"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200 and resp.json().get('code') == '0' and resp.json().get('data'):
                rate = float(resp.json()['data'][0]['fundingRate'])
                results['okx'] = {"rate": rate, "signal": "SELL" if rate > 0.01 else "BUY" if rate < -0.005 else "HOLD"}
        except: pass
        
        # Kraken Futures
        try:
            url = "https://futures.kraken.com/derivatives/api/v3/tickers"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                for ticker in resp.json().get('tickers', []):
                    if ticker.get('symbol') == 'PI_XBTUSD':
                        rate = float(ticker.get('fundingRate', 0))
                        results['kraken'] = {"rate": rate, "signal": "SELL" if rate > 0.01 else "BUY" if rate < -0.005 else "HOLD"}
                        break
        except: pass
        
        # BitMEX
        try:
            url = "https://www.bitmex.com/api/v1/instrument?symbol=XBTUSD"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200 and resp.json():
                rate = float(resp.json()[0].get('fundingRate', 0))
                results['bitmex'] = {"rate": rate, "signal": "SELL" if rate > 0.01 else "BUY" if rate < -0.005 else "HOLD"}
        except: pass
        
        # Gate.io
        try:
            url = "https://api.gateio.ws/api/v4/futures/usdt/contracts/BTC_USDT"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                rate = float(resp.json().get('funding_rate', 0))
                results['gateio'] = {"rate": rate, "signal": "SELL" if rate > 0.01 else "BUY" if rate < -0.005 else "HOLD"}
        except: pass
        

        # Hyperliquid
        try:
            current_time = int(__import__("time").time() * 1000)
            seven_days_ago = current_time - (7 * 24 * 60 * 60 * 1000)
            resp = requests.post(
                "https://api.hyperliquid.xyz/info",
                headers={"Content-Type": "application/json"},
                json={"type": "fundingHistory", "coin": "BTC", "startTime": seven_days_ago},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    rate = float(data[0].get('fundingRate', 0))
                    results['hyperliquid'] = {"rate": rate, "signal": "SELL" if rate > 0.01 else "BUY" if rate < -0.005 else "HOLD"}
        except:
            pass
        

        return results
    
    def _analyze_flow(self, coinbase, kraken, binance_spot, order_books, funding_rates):
        """Analisis flow antar exchange + order book + funding rate"""
        prices = []
        if coinbase.get('price', 0) > 0:
            prices.append(coinbase['price'])
        if kraken.get('last', 0) > 0:
            prices.append(kraken['last'])
        if binance_spot.get('price', 0) > 0:
            prices.append(binance_spot['price'])
        
        if len(prices) < 2:
            return {"signal": "HOLD", "confidence": 50, "reason": "Insufficient data from exchanges"}
        
        avg_price = sum(prices) / len(prices)
        signals = {"BUY": 0, "SELL": 0}
        
        # Arbitrage signals
        if coinbase.get('price', 0) > avg_price * 1.002:
            signals["SELL"] += 1
        elif coinbase.get('price', 0) < avg_price * 0.998:
            signals["BUY"] += 1
        
        if kraken.get('last', 0) > avg_price * 1.002:
            signals["SELL"] += 1
        elif kraken.get('last', 0) < avg_price * 0.998:
            signals["BUY"] += 1
        
        if binance_spot.get('price', 0) > avg_price * 1.002:
            signals["SELL"] += 1
        elif binance_spot.get('price', 0) < avg_price * 0.998:
            signals["BUY"] += 1
        
        # Order book signals (dari semua exchange)
        for ex, ob in order_books.items():
            if ob.get('status') == 'OK':
                bid_ask_ratio = ob.get('bid_ask_ratio', 1)
                if bid_ask_ratio > 1.5:
                    signals["BUY"] += 1
                elif bid_ask_ratio < 0.67:
                    signals["SELL"] += 1
        
        # Funding rate signals
        buy_funding = 0
        sell_funding = 0
        total_rate = 0
        count_rate = 0
        
        for ex, data in funding_rates.items():
            if 'error' not in data and data.get('rate', 0) != 0:
                total_rate += data.get('rate', 0)
                count_rate += 1
                if data.get('signal') == 'BUY':
                    buy_funding += 1
                    signals["BUY"] += 1
                elif data.get('signal') == 'SELL':
                    sell_funding += 1
                    signals["SELL"] += 1
        
        avg_rate = total_rate / count_rate if count_rate > 0 else 0
        total_buy = signals.get("BUY", 0)
        total_sell = signals.get("SELL", 0)
        
        if total_buy >= 5:
            return {"signal": "BUY", "confidence": 75, "reason": f"Strong bullish: Order book + {buy_funding}/{count_rate} funding bullish"}
        if total_sell >= 5:
            return {"signal": "SELL", "confidence": 75, "reason": f"Strong bearish: Order book + {sell_funding}/{count_rate} funding bearish"}
        if total_buy >= 3:
            return {"signal": "BUY", "confidence": 65, "reason": f"Bullish: {buy_funding}/{count_rate} funding bullish"}
        if total_sell >= 3:
            return {"signal": "SELL", "confidence": 65, "reason": f"Bearish: {sell_funding}/{count_rate} funding bearish"}
        return {"signal": "HOLD", "confidence": 50, "reason": f"Neutral: funding avg {avg_rate:.6f}% from {count_rate} exchanges"}
