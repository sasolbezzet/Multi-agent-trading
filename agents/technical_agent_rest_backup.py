#!/usr/bin/env python3
"""
Technical Agent dengan WebSocket Multi-Timeframe
Data real-time via WebSocket KuCoin Futures
"""
import asyncio
import json
import numpy as np
import pandas as pd
import requests
import websockets
from datetime import datetime
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TechnicalAgent:
    def __init__(self):
        self.name = "Technical Analyst (WebSocket MTF)"
        self.ws = None
        self.is_connected = False
        self.ready = False
        
        # Storage untuk setiap timeframe
        self.klines: Dict[str, List] = {
            '5min': [], '15min': [], '30min': [], 
            '1hour': [], '4hour': [], '1day': []
        }
        
        self._max_candles = 200
        self._ws_task = None
        self._message_count = 0
        
        # Start WebSocket di background
        self._ws_task = asyncio.create_task(self._run_websocket())
    
    async def _run_websocket(self):
        """Run WebSocket connection"""
        await self._init_websocket()
        
        # Keep connection alive
        while self.is_connected:
            await asyncio.sleep(1)
    
    async def _init_websocket(self):
        """Inisialisasi WebSocket"""
        try:
            # Dapatkan token
            resp = requests.post("https://api-futures.kucoin.com/api/v1/bullet-public", timeout=10)
            data = resp.json()
            if data.get('code') != '200000':
                logger.error(f"Token error: {data}")
                return
            
            token = data['data']['token']
            endpoint = data['data']['instanceServers'][0]['endpoint']
            ws_url = f"{endpoint}?token={token}"
            
            self.ws = await websockets.connect(ws_url)
            self.is_connected = True
            logger.info("✅ WebSocket connected")
            
            # Subscribe ke semua timeframe
            timeframes = ['5min', '15min', '30min', '1hour', '4hour', '1day']
            for tf in timeframes:
                topic = f"/contractMarket/limitCandle:XBTUSDTM_{tf}"
                subscribe_msg = {
                    "id": str(int(datetime.now().timestamp() * 1000)),
                    "type": "subscribe",
                    "topic": topic,
                    "response": True
                }
                await self.ws.send(json.dumps(subscribe_msg))
                logger.info(f"Subscribed to {tf}")
                await asyncio.sleep(0.3)
            
            # Start listener
            asyncio.create_task(self._listen())
            self.ready = True
            logger.info("✅ WebSocket ready, waiting for data...")
            
        except Exception as e:
            logger.error(f"WebSocket init error: {e}")
            self.is_connected = False
    
    async def _listen(self):
        """Listen untuk pesan WebSocket"""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    
                    if data.get('type') == 'message':
                        topic = data.get('topic', '')
                        candle_data = data.get('data', {})
                        candles = candle_data.get('candles', [])
                        
                        if candles and len(candles) >= 7:
                            # Parse timeframe dari topic
                            for tf in self.klines.keys():
                                if f"_{tf}" in topic:
                                    self._process_candle(tf, candles)
                                    break
                                
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.error(f"Parse error: {e}")
                    
        except Exception as e:
            logger.error(f"Listen error: {e}")
            self.is_connected = False
    
    def _process_candle(self, tf: str, candles: list):
        """Proses candle data"""
        try:
            candle = {
                'time': int(candles[0]),
                'open': float(candles[1]),
                'close': float(candles[2]),
                'high': float(candles[3]),
                'low': float(candles[4]),
                'volume': float(candles[5]),
            }
            
            # Update atau append
            if self.klines[tf] and self.klines[tf][-1]['time'] == candle['time']:
                self.klines[tf][-1] = candle
            else:
                self.klines[tf].append(candle)
                if len(self.klines[tf]) > self._max_candles:
                    self.klines[tf].pop(0)
            
            self._message_count += 1
            if self._message_count % 10 == 0:
                logger.info(f"Data: {tf} close={candle['close']}, total={len(self.klines[tf])}")
                
        except Exception as e:
            logger.error(f"Process error {tf}: {e}")
    
    def _calc_rsi(self, prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        deltas = np.diff(prices[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:]) if len(gains) >= period else np.mean(gains)
        avg_loss = np.mean(losses[-period:]) if len(losses) >= period else np.mean(losses)
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 1)
    
    def _calc_macd(self, prices: List[float]) -> Dict:
        if len(prices) < 26:
            return {'macd': 0, 'signal': 0, 'histogram': 0, 'trend': 'NEUTRAL'}
        series = pd.Series(prices)
        exp1 = series.ewm(span=12, adjust=False).mean()
        exp2 = series.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        current_macd = round(macd.iloc[-1], 2)
        current_signal = round(signal.iloc[-1], 2)
        current_hist = round(histogram.iloc[-1], 2)
        if current_macd > current_signal and current_hist > 0:
            trend = "BULLISH"
        elif current_macd < current_signal and current_hist < 0:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        return {'macd': current_macd, 'signal': current_signal, 'histogram': current_hist, 'trend': trend}
    
    def _calc_bollinger(self, prices: List[float], period: int = 20, std_dev: float = 2) -> Dict:
        if len(prices) < period:
            return {'upper': 0, 'middle': 0, 'lower': 0, 'position': 0.5, 'signal': 'NEUTRAL'}
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        current = prices[-1]
        position = (current - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
        if current <= lower:
            signal = "BUY"
        elif current >= upper:
            signal = "SELL"
        else:
            signal = "NEUTRAL"
        return {'upper': round(upper, 2), 'middle': round(sma, 2), 'lower': round(lower, 2), 'position': round(position, 2), 'signal': signal}
    
    async def analyze(self, main_tf: str = '15min') -> Dict:
        """Analisis teknikal"""
        if not self.ready or not self.klines.get(main_tf, []):
            return self._default_return()
        
        data = self.klines[main_tf]
        if len(data) < 5:
            return self._default_return()
        
        closes = [c['close'] for c in data]
        current_price = closes[-1]
        
        rsi = self._calc_rsi(closes)
        macd = self._calc_macd(closes)
        bb = self._calc_bollinger(closes)
        
        # Signal logic
        if rsi < 35 and bb['position'] < 0.2:
            signal = "BUY"
            confidence = 70
        elif rsi > 65 and bb['position'] > 0.8:
            signal = "SELL"
            confidence = 70
        else:
            signal = "HOLD"
            confidence = 50
        
        return {
            "agent": self.name,
            "signal": signal,
            "confidence": confidence,
            "price": round(current_price, 2),
            "rsi": rsi,
            "macd": macd,
            "bollinger": bb,
            "data_points": len(data),
            "websocket_connected": self.is_connected,
            "timestamp": datetime.now().isoformat()
        }
    
    def _default_return(self):
        return {
            "agent": self.name,
            "signal": "HOLD",
            "confidence": 50,
            "price": 0,
            "rsi": 50,
            "macd": {'macd': 0, 'signal': 0, 'histogram': 0, 'trend': 'NEUTRAL'},
            "bollinger": {'upper': 0, 'middle': 0, 'lower': 0, 'position': 0.5, 'signal': 'NEUTRAL'},
            "data_points": 0,
            "websocket_connected": False,
            "timestamp": datetime.now().isoformat()
        }

async def test():
    agent = TechnicalAgent()
    
    # Tunggu WebSocket ready dan kumpulkan data
    print("Waiting for WebSocket data (30 seconds)...")
    await asyncio.sleep(30)
    
    print("\n" + "=" * 60)
    print("TECHNICAL AGENT WEBSOCKET TEST")
    print("=" * 60)
    
    for tf in ['5min', '15min', '30min', '1hour', '4hour', '1day']:
        result = await agent.analyze(tf)
        data_points = result.get('data_points', 0)
        if data_points > 0:
            print(f"\n📊 {tf.upper()}:")
            print(f"   Signal: {result['signal']} ({result['confidence']}%)")
            print(f"   Price: ${result['price']:,.2f}")
            print(f"   RSI: {result['rsi']}")
            print(f"   Data: {data_points} candles")
        else:
            print(f"\n⚠️ {tf.upper()}: No data yet (need more time)")

if __name__ == "__main__":
    asyncio.run(test())
