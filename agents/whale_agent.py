#!/usr/bin/env python3
"""
Whale Agent - Analisa inflow, outflow, dan whale transactions
Menggunakan async parallel untuk SEMUA exchange
"""

import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import time
import asyncio

load_dotenv()

class WhaleAgent:
    def __init__(self):
        self.name = "Whale & On-Chain Analyst"
        self.arkham_api_key = os.getenv("ARKHAM_API_KEY")
        self.arkham_headers = {"API-Key": self.arkham_api_key} if self.arkham_api_key else {}
        self.arkham_base = "https://api.arkm.com"
        
        # SEMUA exchange yang dipantau (19 exchange)
        self.exchanges = [
            "binance", "coinbase", "okx", "bybit", "kraken", "kucoin",
            "bitfinex", "bitstamp", "huobi", "poloniex", "gemini",
            "mexc", "bitget", "phemex"
        ]
        
        # Threshold dalam JUTA USD
        self.THRESHOLD_STRONG = 200   # $200M
        self.THRESHOLD_MODERATE = 100  # $100M
        
        # Cache
        self._cache = None
        self._cache_time = 0

    async def _fetch_inflow_for_exchange(self, exchange):
        """Fetch inflow untuk satu exchange (dijalankan parallel)"""
        try:
            url = f"{self.arkham_base}/transfers"
            params = {
                "to": exchange,
                "usdGte": "10000000",
                "timeLast": "24h",
                "limit": 3
            }
            resp = requests.get(url, headers=self.arkham_headers, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                transfers = data.get('transfers', [])
                if transfers:
                    exchange_inflow = sum(t.get('historicalUSD', 0) for t in transfers[:3])
                else:
                    exchange_inflow = 0
                return exchange, exchange_inflow
        except Exception as e:
            pass
        return exchange, 0

    async def _fetch_outflow_for_exchange(self, exchange):
        """Fetch outflow untuk satu exchange (dijalankan parallel)"""
        try:
            url = f"{self.arkham_base}/transfers"
            params = {
                "from": exchange,
                "usdGte": "10000000",
                "timeLast": "24h",
                "limit": 3
            }
            resp = requests.get(url, headers=self.arkham_headers, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                transfers = data.get('transfers', [])
                if transfers:
                    exchange_outflow = sum(t.get('historicalUSD', 0) for t in transfers[:3])
                else:
                    exchange_outflow = 0
                return exchange, exchange_outflow
        except Exception as e:
            pass
        return exchange, 0

    async def _fetch_whale_tx_for_exchange(self, exchange):
        """Fetch whale transaction count untuk satu exchange"""
        try:
            url = f"{self.arkham_base}/transfers"
            params = {
                "to": exchange,
                "usdGte": "1000000",
                "timeLast": "24h",
                "limit": 100
            }
            resp = requests.get(url, headers=self.arkham_headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                transfers = data.get('transfers', [])
                return len(transfers)
        except:
            pass
        return 0

    async def _get_inflow_parallel(self):
        """Ambil inflow dari semua exchange secara parallel"""
        tasks = [self._fetch_inflow_for_exchange(ex) for ex in self.exchanges]
        results = await asyncio.gather(*tasks)
        
        total_inflow = 0
        exchange_details = {}
        
        for exchange, inflow in results:
            total_inflow += inflow
            if inflow > 0:
                exchange_details[exchange] = round(inflow / 1_000_000, 1)
        
        return total_inflow, exchange_details

    async def _get_outflow_parallel(self):
        """Ambil outflow dari semua exchange secara parallel"""
        tasks = [self._fetch_outflow_for_exchange(ex) for ex in self.exchanges]
        results = await asyncio.gather(*tasks)
        
        total_outflow = 0
        exchange_details = {}
        
        for exchange, outflow in results:
            total_outflow += outflow
            if outflow > 0:
                exchange_details[exchange] = round(outflow / 1_000_000, 1)
        
        return total_outflow, exchange_details

    async def _get_whale_tx_parallel(self):
        """Ambil whale transactions dari semua exchange secara parallel"""
        tasks = [self._fetch_whale_tx_for_exchange(ex) for ex in self.exchanges[:10]]
        results = await asyncio.gather(*tasks)
        return sum(results)

    async def analyze(self):
        """Analisis whale dengan async parallel untuk SEMUA exchange"""
        import time
        
        # Cache 2 menit
        if self._cache and (time.time() - self._cache_time) < 120:
            return self._cache
        
        print(f"🐋 Whale Agent: Fetching data from {len(self.exchanges)} exchanges in parallel...")
        start_time = time.time()
        
        # Jalankan semua request secara parallel
        inflow_task = self._get_inflow_parallel()
        outflow_task = self._get_outflow_parallel()
        whale_tx_task = self._get_whale_tx_parallel()
        
        # Tunggu semua selesai
        (total_inflow, inflow_exchanges), (total_outflow, outflow_exchanges), total_whale_tx = await asyncio.gather(
            inflow_task, outflow_task, whale_tx_task
        )
        
        elapsed = time.time() - start_time
        print(f"   ✅ Completed in {elapsed:.2f}s (parallel)")
        
        # Konversi ke JUTA USD
        total_inflow_m = round(total_inflow / 1_000_000, 1)
        total_outflow_m = round(total_outflow / 1_000_000, 1)
        
        # Hitung NET FLOW
        net_flow_m = round(total_outflow_m - total_inflow_m, 1)
        
        # Logika signal
        if net_flow_m > self.THRESHOLD_STRONG:
            signal = "BUY"
            confidence = 85
            reason = f"🔥 STRONG ACCUMULATION: Net outflow ${net_flow_m:.0f}M | Whale TX: {total_whale_tx}"
        elif net_flow_m > self.THRESHOLD_MODERATE:
            signal = "BUY"
            confidence = 70
            reason = f"📈 ACCUMULATION: Net outflow ${net_flow_m:.0f}M"
        elif net_flow_m < -self.THRESHOLD_STRONG:
            signal = "SELL"
            confidence = 85
            reason = f"🔥 STRONG DISTRIBUTION: Net inflow ${abs(net_flow_m):.0f}M"
        elif net_flow_m < -self.THRESHOLD_MODERATE:
            signal = "SELL"
            confidence = 70
            reason = f"📉 DISTRIBUTION: Net inflow ${abs(net_flow_m):.0f}M"
        else:
            signal = "HOLD"
            confidence = 50
            reason = f"⚖️ NEUTRAL: Net flow ${net_flow_m:+.1f}M"
        
        result = {
            "agent": self.name,
            "signal": signal,
            "confidence": confidence,
            "reason": reason,
            "total_inflow_m": total_inflow_m,
            "total_outflow_m": total_outflow_m,
            "net_flow_m": net_flow_m,
            "total_whale_tx": total_whale_tx,
            "inflow_exchanges": inflow_exchanges,
            "outflow_exchanges": outflow_exchanges,
            "parallel_time_sec": round(elapsed, 2),
            "timestamp": datetime.now().isoformat()
        }
        
        self._cache = result
        self._cache_time = time.time()
        return result

if __name__ == "__main__":
    import asyncio
    async def test():
        agent = WhaleAgent()
        result = await agent.analyze()
        print(f"\n🐋 WHALE AGENT (PARALLEL - {len(agent.exchanges)} exchanges):")
        print(f"   Signal: {result['signal']} ({result['confidence']}%)")
        print(f"   Net Flow: ${result['net_flow_m']:+.1f}M")
        print(f"   Total Whale TX: {result['total_whale_tx']}")
        print(f"   Time: {result['parallel_time_sec']}s")
    asyncio.run(test())
