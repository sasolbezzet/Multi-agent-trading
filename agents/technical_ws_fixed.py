#!/usr/bin/env python3
"""
Technical Agent dengan WebSocket Multi-Timeframe
Menggunakan library kucoin-futures-python yang resmi
"""
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List
import logging

from kucoin_futures.client import Market
from kucoin_futures.ws_client import KucoinFuturesWsClient
from kucoin_futures.client import WsToken

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TechnicalAgentWS:
    def __init__(self):
        self.name = "Technical Analyst (WebSocket MTF)"
        self.ws_client = None
        self.is_connected = False
        
        # Storage untuk setiap timeframe
        self.klines: Dict[str, List] = {
            '1min': [], '5min': [], '15min': [], '30min': [], 
            '1hour': [], '2hour': [], '4hour': [], '1day': []
        }
        
        self._max_candles = 200
        self._initialized = False
        
        # Start WebSocket
        asyncio.create_task(self._init_websocket())
    
    async def _init_websocket(self):
        """Inisialisasi WebSocket menggunakan library resmi"""
        try:
            # Callback untuk menangani pesan
            async def handle_message(msg):
                await self._process_message(msg)
            
            # Buat client
            client = WsToken()
            self.ws_client = await KucoinFuturesWsClient.create(
                asyncio.get_event_loop(), 
                client, 
                handle_message,
                private=False
            )
            
            # Subscribe ke semua timeframe
            timeframes = ['1min', '5min', '15min', '30min', '1hour', '2hour', '4hour', '1day']
            for tf in timeframes:
                topic = f"/contractMarket/limitCandle:XBTUSDTM_{tf}"
                await self.ws_client.subscribe(topic)
                logger.info(f"Subscribed to {tf}")
                await asyncio.sleep(0.2)
            
            self.is_connected = True
            self._initialized = True
            logger.info("✅ WebSocket multi-timeframe connected")
            
        except Exception as e:
            logger.error(f"WebSocket init error: {e}")
            self._initialized = False
    
    async def _process_message(self, msg: dict):
        """Proses pesan WebSocket yang masuk"""
        try:
            topic = msg.get('topic', '')
            data = msg.get('data', {})
            
            # Parse timeframe dari topic
            for tf in self.klines.keys():
                if f"_{tf}" in topic:
                    candles = data.get('candles', [])
                    if candles and len(candles) >= 7:
                        candle = {
                            'time': int(candles[0]),
                            'open': float(candles[1]),
                            'close': float(candles[2]),
                            'high': float(candles[3]),
                            'low': float(candles[4]),
                            'volume': float(candles[5]),
                        }
                        self.klines[tf].append(candle)
                        if len(self.klines[tf]) > self._max_candles:
                            self.klines[tf].pop(0)
                    break
                    
        except Exception as e:
            logger.error(f"Process message error: {e}")
    
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
        if not self._initialized or not self.klines.get(main_tf, []):
            return self._default_return()
        
        data = self.klines[main_tf]
        if len(data) < 30:
            return self._default_return()
        
        closes = [c['close'] for c in data]
        highs = [c['high'] for c in data]
        lows = [c['low'] for c in data]
        volumes = [c['volume'] for c in data]
        current_price = closes[-1]
        
        rsi = self._calc_rsi(closes)
        macd = self._calc_macd(closes)
        bb = self._calc_bollinger(closes)
        
        # Simple signal
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
    agent = TechnicalAgentWS()
    await asyncio.sleep(15)
    result = await agent.analyze('15min')
    print(f"\n📊 HASIL TEST:")
    print(f"   Signal: {result['signal']} ({result['confidence']}%)")
    print(f"   RSI: {result['rsi']}")
    print(f"   WebSocket: {result['websocket_connected']}")
    print(f"   Data points: {result['data_points']}")

if __name__ == "__main__":
    asyncio.run(test())
