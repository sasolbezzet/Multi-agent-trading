#!/usr/bin/env python3
"""
Exchange Agent - Analisa volume, OI, funding rate dari multiple exchange
"""

import requests
import os
from datetime import datetime
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class ExchangeAgent:
    def __init__(self):
        self.name = "Exchange Flow Analyst"
        self.api_key = os.getenv('KUCOIN_API_KEY')

    async def _get_kucoin_futures_data(self):
        """Ambil volume dan OI dari KuCoin Futures"""
        try:
            url = "https://api-futures.kucoin.com/api/v1/contracts/XBTUSDTM"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == '200000':
                    contract = data['data']
                    return {
                        'volume_24h': float(contract.get('volumeOf24h', 0)),
                        'open_interest': float(contract.get('openInterest', 0)),
                        'mark_price': float(contract.get('markPrice', 0)),
                        'funding_rate': float(contract.get('fundingRate', 0))
                    }
        except Exception as e:
            print(f"KuCoin futures error: {e}")
        return {'volume_24h': 0, 'open_interest': 0, 'mark_price': 0, 'funding_rate': 0}

    async def _get_coinbase_price(self):
        """Ambil harga dari Coinbase"""
        try:
            resp = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return float(data['data']['amount'])
        except:
            pass
        return 0

    async def _get_kraken_price(self):
        """Ambil harga dari Kraken"""
        try:
            resp = requests.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return float(data['result']['XXBTZUSD']['c'][0])
        except:
            pass
        return 0

    async def _get_binance_price(self):
        """Ambil harga dari Binance"""
        try:
            resp = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return float(data['price'])
        except:
            pass
        return 0

    async def _get_bybit_price(self):
        """Ambil harga dari Bybit"""
        try:
            resp = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('retCode') == 0:
                    return float(data['result']['list'][0]['lastPrice'])
        except:
            pass
        return 0

    async def _get_okx_price(self):
        """Ambil harga dari OKX"""
        try:
            resp = requests.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == '0':
                    return float(data['data'][0]['last'])
        except:
            pass
        return 0

    async def _get_kucoin_spot_price(self):
        """Ambil harga dari KuCoin Spot"""
        try:
            resp = requests.get("https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=BTC-USDT", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == '200000':
                    return float(data['data']['price'])
        except:
            pass
        return 0

    async def _get_huobi_price(self):
        """Ambil harga dari Huobi"""
        try:
            resp = requests.get("https://api.huobi.pro/market/detail/merged?symbol=btcusdt", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 'ok':
                    return float(data['tick']['close'])
        except:
            pass
        return 0

    async def _get_binance_funding_rate(self):
        """Ambil funding rate dari Binance Futures"""
        try:
            resp = requests.get("https://dapi.binance.com/dapi/v1/fundingRate?symbol=BTCUSD_PERP&limit=1", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return float(data[0]['fundingRate'])
        except:
            pass
        return 0

    async def _get_bybit_funding_rate(self):
        """Ambil funding rate dari Bybit Futures"""
        try:
            resp = requests.get("https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('retCode') == 0:
                    return float(data['result']['list'][0]['fundingRate'])
        except:
            pass
        return 0

    async def _get_okx_funding_rate(self):
        """Ambil funding rate dari OKX Futures"""
        try:
            resp = requests.get("https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USD-SWAP", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == '0' and data.get('data'):
                    return float(data['data'][0]['fundingRate'])
        except:
            pass
        return 0

    async def analyze(self):
        """Analisis exchange flow"""
        
        # Ambil data dari KuCoin Futures
        kucoin_data = await self._get_kucoin_futures_data()
        volume_24h = kucoin_data['volume_24h']
        open_interest = kucoin_data['open_interest']
        kucoin_funding = kucoin_data['funding_rate']
        
        # Ambil funding rate dari berbagai exchange
        binance_funding = await self._get_binance_funding_rate()
        bybit_funding = await self._get_bybit_funding_rate()
        okx_funding = await self._get_okx_funding_rate()
        
        # Hitung rata-rata funding rate
        funding_rates = [kucoin_funding, binance_funding, bybit_funding, okx_funding]
        valid_rates = [r for r in funding_rates if r != 0]
        avg_funding = sum(valid_rates) / len(valid_rates) if valid_rates else 0
        avg_funding_bps = avg_funding * 10000
        
        # Ambil harga dari 7 exchange
        prices = []
        price_sources = {}
        
        coinbase = await self._get_coinbase_price()
        if coinbase > 0:
            prices.append(coinbase)
            price_sources['coinbase'] = coinbase
        
        kraken = await self._get_kraken_price()
        if kraken > 0:
            prices.append(kraken)
            price_sources['kraken'] = kraken
        
        binance = await self._get_binance_price()
        if binance > 0:
            prices.append(binance)
            price_sources['binance'] = binance
        
        bybit = await self._get_bybit_price()
        if bybit > 0:
            prices.append(bybit)
            price_sources['bybit'] = bybit
        
        okx = await self._get_okx_price()
        if okx > 0:
            prices.append(okx)
            price_sources['okx'] = okx
        
        kucoin_spot = await self._get_kucoin_spot_price()
        if kucoin_spot > 0:
            prices.append(kucoin_spot)
            price_sources['kucoin'] = kucoin_spot
        
        huobi = await self._get_huobi_price()
        if huobi > 0:
            prices.append(huobi)
            price_sources['huobi'] = huobi
        
        # Hitung rata-rata harga dan trend
        if len(prices) >= 3:
            avg_price = sum(prices) / len(prices)
            current_price = prices[-1]
            if current_price > avg_price * 1.002:
                price_direction = "📈 BULLISH"
                price_trend = "uptrend"
            elif current_price < avg_price * 0.998:
                price_direction = "📉 BEARISH"
                price_trend = "downtrend"
            else:
                price_direction = "➡️ NEUTRAL"
                price_trend = "neutral"
        else:
            price_direction = "➡️ NEUTRAL"
            price_trend = "neutral"
        
        # Volume direction
        if volume_24h > 5000:
            volume_surge = 'high'
            volume_direction = "📈 HIGH"
        elif volume_24h > 2000:
            volume_surge = 'normal'
            volume_direction = "➡️ NORMAL"
        else:
            volume_surge = 'low'
            volume_direction = "📉 LOW"
        
        # OI direction
        if open_interest > 30000000:
            oi_trend = 'increasing'
            oi_direction = "📈 BULLISH"
        elif open_interest < 25000000:
            oi_trend = 'decreasing'
            oi_direction = "📉 BEARISH"
        else:
            oi_trend = 'stable'
            oi_direction = "➡️ NEUTRAL"
        
        # Funding direction
        if avg_funding_bps > 5:
            funding_direction = f"📈 POSITIVE ({avg_funding_bps:.1f} bps)"
        elif avg_funding_bps < -5:
            funding_direction = f"📉 NEGATIVE ({avg_funding_bps:.1f} bps)"
        else:
            funding_direction = f"➡️ NEUTRAL ({avg_funding_bps:.1f} bps)"
        
        # Signal logic
        if volume_surge == 'high' and oi_trend == 'increasing' and price_trend == 'uptrend':
            signal = "BUY"
            confidence = 75
            reason = f"🔥 HIGH VOLUME ({volume_24h:,.0f}) + OI rising + uptrend"
        elif volume_surge == 'high' and oi_trend == 'increasing':
            signal = "BUY"
            confidence = 65
            reason = f"🔥 HIGH VOLUME ({volume_24h:,.0f}) + OI rising"
        elif volume_surge == 'high' and price_trend == 'uptrend':
            signal = "BUY"
            confidence = 60
            reason = f"📈 HIGH VOLUME ({volume_24h:,.0f}) + uptrend"
        elif volume_surge == 'high' and oi_trend == 'decreasing':
            signal = "SELL"
            confidence = 65
            reason = f"📉 HIGH VOLUME ({volume_24h:,.0f}) + OI falling"
        elif volume_surge == 'high' and price_trend == 'downtrend':
            signal = "SELL"
            confidence = 60
            reason = f"📉 HIGH VOLUME ({volume_24h:,.0f}) + downtrend"
        else:
            signal = "HOLD"
            confidence = 50
            reason = f"Volume: {volume_surge}, OI: {oi_trend}, Trend: {price_trend} - Neutral"
        
        return {
            "agent": self.name,
            "signal": signal,
            "confidence": confidence,
            "reason": f"{reason} | Avg funding: {avg_funding_bps:.2f} bps",
            "volume_24h": volume_24h,
            "volume_surge": volume_surge,
            "volume_direction": volume_direction,
            "open_interest": open_interest,
            "oi_trend": oi_trend,
            "oi_direction": oi_direction,
            "price_direction": price_direction,
            "funding_direction": funding_direction,
            "funding_rate": avg_funding,
            "funding_bps": avg_funding_bps,
            "prices": price_sources,
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import asyncio
    async def test():
        agent = ExchangeAgent()
        result = await agent.analyze()
        print("\n📊 EXCHANGE AGENT:")
        print(f"   Signal: {result['signal']} ({result['confidence']}%)")
        print(f"   Volume: {result['volume_24h']:,.0f} BTC ({result['volume_direction']})")
        print(f"   OI: {result['oi_direction']}")
        print(f"   Funding: {result['funding_direction']}")
        print(f"   Price: {result['price_direction']}")
        print(f"   Prices: {result['prices']}")
    asyncio.run(test())
