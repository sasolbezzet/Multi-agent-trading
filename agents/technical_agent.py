#!/usr/bin/env python3
"""
Technical Agent dengan Multi-Timeframe Analysis
Timeframes: 15m, 1h, 4h, 1d
Semua timeframe digunakan untuk analisis dan perhitungan
"""

import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TechnicalAgent:

    
    def _detect_candle_pattern(self, df):
        """Deteksi candlestick patterns"""
        if len(df) < 3:
            return []
        
        patterns = []
        
        # Ambil candle terakhir dan sebelumnya
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        open_p = last['Open']
        high = last['High']
        low = last['Low']
        close = last['Close']
        body = abs(close - open_p)
        upper_wick = high - max(open_p, close)
        lower_wick = min(open_p, close) - low
        total_range = high - low
        
        # 1. DOJI (body sangat kecil)
        if total_range > 0 and body / total_range < 0.1:
            patterns.append("DOJI")
        
        # 2. HAMMER (body kecil, lower wick panjang, terjadi setelah downtrend)
        if prev and prev['Close'] < prev['Open']:  # candle sebelumnya merah (turun)
            if body / total_range < 0.3 and lower_wick > body * 2 and upper_wick < body:
                patterns.append("HAMMER")
        
        # 3. BULLISH ENGULFING
        if prev:
            prev_body = abs(prev['Close'] - prev['Open'])
            if close > open_p and prev['Close'] < prev['Open']:  # hijau menutupi merah
                if body > prev_body and close > prev['Open'] and open_p < prev['Close']:
                    patterns.append("BULLISH_ENGULFING")
        
        return patterns


    def __init__(self):
        self.name = "Technical Analyst (Multi-Timeframe)"
        self.symbol = "BTC-USD"
        
        # Konfigurasi timeframe - SEMUA DIGUNAKAN
        self.timeframes = {
            '15m': {'interval': '15m', 'period': '2d', 'weight': 1},
            '1h': {'interval': '60m', 'period': '7d', 'weight': 2},
            '4h': {'interval': '1h', 'period': '30d', 'weight': 3},
            '1d': {'interval': '1d', 'period': '90d', 'weight': 4}
        }
        
        self.rsi_period = 14
        self.bb_period = 20
        self.bb_std = 2

    def _fetch_data(self, interval, period):
        """Fetch data dari Yahoo Finance"""
        try:
            ticker = yf.Ticker(self.symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty or len(df) < 20:
                return None
            return df
        except Exception as e:
            logger.error(f"Fetch error {interval}: {e}")
            return None

    def _calculate_rsi(self, prices, period=14):
        if len(prices) < period + 1:
            return 50.0
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:]) if len(gains) >= period else np.mean(gains)
        avg_loss = np.mean(losses[-period:]) if len(losses) >= period else np.mean(losses)
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 1)

    def _calculate_macd(self, prices):
        if len(prices) < 26:
            return {'trend': 'NEUTRAL', 'macd': 0, 'signal': 0}
        series = pd.Series(prices)
        exp1 = series.ewm(span=12, adjust=False).mean()
        exp2 = series.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        current_macd = macd.iloc[-1]
        current_signal = signal.iloc[-1]
        if current_macd > current_signal:
            trend = "BULLISH"
        elif current_macd < current_signal:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        return {'trend': trend, 'macd': round(current_macd, 2), 'signal': round(current_signal, 2)}

    def _calculate_bollinger(self, prices, period=20, std=2):
        if len(prices) < period:
            return {'signal': 'NEUTRAL', 'upper': 0, 'middle': 0, 'lower': 0, 'position': 0.5}
        sma = np.mean(prices[-period:])
        std_dev = np.std(prices[-period:])
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        current = prices[-1]
        position = (current - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
        if current <= lower:
            signal = "BUY"
        elif current >= upper:
            signal = "SELL"
        else:
            signal = "NEUTRAL"
        return {
            'signal': signal,
            'upper': round(upper, 2),
            'middle': round(sma, 2),
            'lower': round(lower, 2),
            'position': round(position, 2)
        }

    def _analyze_timeframe(self, tf_name, config):
        """Analisis satu timeframe - lengkap dengan semua indikator"""
        try:
            df = self._fetch_data(config['interval'], config['period'])
            if df is None or len(df) < 20:
                return None
            
            closes = df['Close'].values
            volumes = df['Volume'].values
            current_price = closes[-1]
            
            # Hitung semua indikator
            rsi = self._calculate_rsi(closes)
            macd = self._calculate_macd(closes)
            bb = self._calculate_bollinger(closes)
            
            # SMA
            sma_20 = np.mean(closes[-20:]) if len(closes) >= 20 else current_price
            sma_50 = np.mean(closes[-50:]) if len(closes) >= 50 else current_price
            
            # Volume ratio
            avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
            volume_ratio = round(volumes[-1] / avg_volume, 2) if avg_volume > 0 else 1.0
            
            # Scoring (0-100) berdasarkan semua indikator
            score = 50
            
            # SMA Crossover (bobot 25)
            if sma_20 > sma_50:
                score += 15
            else:
                score -= 15
            
            # RSI (bobot 25)
            if rsi > 70:
                score -= 10  # overbought
            elif rsi < 30:
                score += 10  # oversold
            elif rsi > 55:
                score += 5
            elif rsi < 45:
                score -= 5
            
            # MACD (bobot 25)
            if macd['trend'] == 'BULLISH':
                score += 12
            elif macd['trend'] == 'BEARISH':
                score -= 12
            
            # Bollinger Bands (bobot 25)
            if bb['signal'] == 'BUY':
                score += 8
            elif bb['signal'] == 'SELL':
                score -= 8
            
            # Tentukan signal berdasarkan score
            if score >= 65:
                signal = "BUY"
                confidence = min(85, score)
            elif score <= 35:
                signal = "SELL"
                confidence = min(85, 100 - score)
            else:
                signal = "HOLD"
                confidence = 50
            
            return {
                'timeframe': tf_name,
                'signal': signal,
                'confidence': confidence,
                'score': score,
                'rsi': rsi,
                'macd': macd['trend'],
                'macd_value': macd.get('macd', 0),
                'macd_signal': macd.get('signal', 0),
                'bb_signal': bb['signal'],
                'bb_upper': bb['upper'],
                'bb_middle': bb['middle'],
                'bb_lower': bb['lower'],
                'bb_position': bb['position'],
                'volume_ratio': volume_ratio,
                'sma_20': round(sma_20, 2),
                'sma_50': round(sma_50, 2),
                'price': current_price
            }
        except Exception as e:
            logger.error(f"Error analyzing {tf_name}: {e}")
            return None

    async def analyze(self):
        candle_patterns = []
        """
        Analisis multi-timeframe menggunakan SEMUA timeframe
        Menghasilkan weighted signal berdasarkan bobot
        """
        results = {}
        total_weight = 0
        weighted_score = 0
        all_volume_ratios = []
        one_day_volume = 1.0
        
        print(f"\n📊 Analisis Multi-Timeframe: {', '.join(self.timeframes.keys())}")
        
        for tf_name, config in self.timeframes.items():
            result = self._analyze_timeframe(tf_name, config)
            if result:
                results[tf_name] = result
                total_weight += config['weight']
                weighted_score += result['score'] * config['weight']
                all_volume_ratios.append(result['volume_ratio'])
                print(f"   {tf_name}: {result['signal']} ({result['confidence']}%) | Score: {result['score']} | Vol: {result['volume_ratio']}x | RSI: {result['rsi']}")
            else:
                print(f"   {tf_name}: ❌ Gagal fetch data")
        
        if total_weight == 0:
            return self._default_result()
        
        # Final score dari weighted average
        final_score = weighted_score / total_weight
        
        # Volume ratio: rata-rata dari semua timeframe (atau bisa pakai max)
        avg_volume_ratio = round(sum(all_volume_ratios) / len(all_volume_ratios), 2) if all_volume_ratios else 1.0
        max_volume_ratio = max(all_volume_ratios) if all_volume_ratios else 1.0
        
        # Tentukan final signal
        if final_score >= 65:
            signal = "BUY"
            confidence = min(85, int(final_score))
        elif final_score <= 35:
            signal = "SELL"
            confidence = min(85, int(100 - final_score))
        else:
            signal = "HOLD"
            confidence = 50
        
        # Ambil data dari timeframe 1h untuk detail utama
        main_result = results.get('1h', {})
        
        return {
            "agent": self.name,
            "signal": signal,
            "confidence": confidence,
            "trend": "bullish" if signal == "BUY" else "bearish" if signal == "SELL" else "neutral",
            "final_score": round(final_score, 1),
            # Detail dari semua timeframe
            "candle_patterns": candle_patterns,
            "multi_timeframe_results": results,
            # Detail utama (dari 1h)
            "rsi": main_result.get("rsi", 50),
            "macd": {'trend': main_result.get('macd', 'NEUTRAL')},
            "bollinger": {'signal': main_result.get('bb_signal', 'NEUTRAL')},
            "volume_ratio": one_day_volume,  # volume dari timeframe 1d untuk risk agent
            "max_volume_ratio": max_volume_ratio,  # volume tertinggi
            "avg_volume_ratio": avg_volume_ratio,  # rata-rata semua timeframe (untuk analisa)
            "atr_percent": 0.5,
            "price": main_result.get('price', 0),
            "timestamp": datetime.now().isoformat()
        }
    
    def _default_result(self):
        return {
            "agent": self.name,
            "signal": "HOLD",
            "confidence": 50,
            "trend": "neutral",
            "final_score": 50,
            "multi_timeframe_results": {},
            "rsi": 50,
            "macd": {'trend': 'NEUTRAL'},
            "bollinger": {'signal': 'NEUTRAL'},
            "volume_ratio": 1.0,
            "max_volume_ratio": 1.0,
            "atr_percent": 0.5,
            "price": 0,
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import asyncio
    async def test():
        agent = TechnicalAgent()
        result = await agent.analyze()
        print(f"\n" + "="*50)
        print(f"✅ FINAL SIGNAL: {result['signal']} ({result['confidence']}%)")
        print(f"   Final Score: {result['final_score']}")
        print(f"   Volume Ratio (rata-rata): {result['volume_ratio']}x")
        print(f"   Volume Ratio (max): {result['max_volume_ratio']}x")
        print(f"   RSI (1h): {result['rsi']}")
        print(f"   MACD: {result['macd']['trend']}")
        print(f"   Bollinger: {result['bollinger']['signal']}")
        print("="*50)
        
        print("\n📈 PER TIMEFRAME:")
        for tf, res in result.get('multi_timeframe_results', {}).items():
            print(f"   {tf}: {res['signal']} | Score: {res['score']} | RSI: {res['rsi']} | Vol: {res['volume_ratio']}x")
    asyncio.run(test())
