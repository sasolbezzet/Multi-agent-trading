import yfinance as yf
import numpy as np
from datetime import datetime

class TechnicalAgent:


    async def _get_guavy_indicators(self):
        """Ambil indikator teknikal dari Guavy API"""
        try:
            import requests
            import os
            
            env_path = '/home/ubuntu/groq_trading_bot/.env'
            with open(env_path) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
            
            api_key = os.getenv('GUAVY_API_KEY')
            if not api_key:
                return None
            
            url = "https://data.guavy.com/api/v1/technical-analysis/get-indicators/BTC"
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                indicators = data.get('indicators', {})
                macd_data = indicators.get('macd', {})
                bollinger = indicators.get('bollinger_bands', {})
                
                return {
                    "rsi": indicators.get('rsi'),
                    "macd": macd_data.get('value'),
                    "macd_signal": macd_data.get('signal'),
                    "adx": indicators.get('adx'),
                    "atr": indicators.get('atr'),
                    "bollinger_upper": bollinger.get('upper'),
                    "bollinger_lower": bollinger.get('lower'),
                    "ema": indicators.get('ema'),
                    "source": "Guavy"
                }
        except Exception as e:
            print(f"Guavy error: {e}")
        return None

    def __init__(self):
        self.name = "Technical Analyst"
        # Multiple timeframes dengan bobot
        self.timeframes = {
            "15m": {"interval": "15m", "period": "2d", "weight": 0.25},
            "1h": {"interval": "60m", "period": "7d", "weight": 0.35},
            "4h": {"interval": "4h", "period": "14d", "weight": 0.25},
            "1d": {"interval": "1d", "period": "30d", "weight": 0.15},
        }
    
    async def analyze(self, symbol="BTC-USD"):
        guavy_indicators = await self._get_guavy_indicators()
        """Analisis multi-timeframe (15m, 1h, 4h, 1d) + Volume + S/R"""
        timeframe_signals = {}
        weighted_buy = 0
        weighted_sell = 0
        weighted_neutral = 0
        total_weight = 0
        latest_price = 0
        
        # Untuk kalkulasi support/resistance global
        all_prices = []
        all_volumes = []
        
        for tf_name, config in self.timeframes.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=config["period"], interval=config["interval"])
                
                if hist.empty:
                    continue
                
                prices = hist['Close'].values
                volumes = hist['Volume'].values
                
                # Analisis pola chart dengan AI untuk semua timeframe
                # Simpan hasil dari setiap timeframe, nanti ambil yang confidence tertinggi
                if not hasattr(self, '_ai_patterns'):
                    self._ai_patterns = []
                
                tf_result = await self._analyze_patterns_with_ai(prices, volumes, tf_name)
                if tf_result:
                    tf_result['timeframe'] = tf_name
                    self._ai_patterns.append(tf_result)
                current_price = prices[-1]
                latest_price = current_price
                
                # Kumpulkan untuk S/R global
                all_prices.extend(prices[-50:])
                all_volumes.extend(volumes[-50:])
                
                # Hitung RSI
                rsi = self._calculate_rsi(prices)
                
                # Hitung MACD
                macd, macd_signal = self._calculate_macd(prices)
                
                # Hitung SMA
                sma_20 = prices[-20:].mean() if len(prices) >= 20 else current_price
                sma_50 = prices[-50:].mean() if len(prices) >= 50 else current_price
                
                # ========== VOLUME ANALYSIS ==========
                avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else volumes[-1]
                current_volume = volumes[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
                
                # Hitung ATR untuk dynamic stop loss
                atr = self.calculate_atr(hist['High'].values, hist['Low'].values, prices, 14)
                atr_percent = (atr / current_price) * 100 if current_price > 0 else 1.5
                
                # Hitung Bollinger Bands
                upper_band, middle_band, lower_band = self.calculate_bollinger(prices, 20, 2)
                bb_position = (current_price - lower_band) / (upper_band - lower_band) if (upper_band - lower_band) > 0 else 0.5
                
                # Bollinger Bands signal
                bb_signal = "NEUTRAL"
                bb_confidence = 0
                if current_price <= lower_band:
                    bb_signal = "BUY"
                    bb_confidence = 20
                elif current_price >= upper_band:
                    bb_signal = "SELL"
                    bb_confidence = -20
                elif bb_position < 0.2:
                    bb_signal = "BUY"
                    bb_confidence = 10
                elif bb_position > 0.8:
                    bb_signal = "SELL"
                    bb_confidence = -10
                
                # Volume signal
                volume_signal = "NEUTRAL"
                volume_confidence = 0
                if volume_ratio > 1.5:
                    volume_signal = "HIGH_VOLUME"
                    volume_confidence = 15 if volume_ratio > 2 else 10
                elif volume_ratio < 0.5:
                    volume_signal = "LOW_VOLUME"
                    volume_confidence = -10
                
                # ========== SUPPORT & RESISTANCE ==========
                # Cari level support (local minimum) dan resistance (local maximum)
                lookback = min(20, len(prices))
                recent_prices = prices[-lookback:]
                
                # Resistance: titik tertinggi lokal
                resistance_levels = []
                support_levels = []
                
                for i in range(2, len(recent_prices)-2):
                    if recent_prices[i] > recent_prices[i-1] and recent_prices[i] > recent_prices[i-2] and recent_prices[i] > recent_prices[i+1] and recent_prices[i] > recent_prices[i+2]:
                        resistance_levels.append(recent_prices[i])
                    if recent_prices[i] < recent_prices[i-1] and recent_prices[i] < recent_prices[i-2] and recent_prices[i] < recent_prices[i+1] and recent_prices[i] < recent_prices[i+2]:
                        support_levels.append(recent_prices[i])
                
                nearest_resistance = min([r for r in resistance_levels if r > current_price], default=current_price * 1.03)
                nearest_support = max([s for s in support_levels if s < current_price], default=current_price * 0.97)
                
                # Sinyal dari S/R
                sr_signal = "NEUTRAL"
                sr_confidence = 0
                if current_price <= nearest_support * 1.005:
                    sr_signal = "BUY"
                    sr_confidence = 15
                elif current_price >= nearest_resistance * 0.995:
                    sr_signal = "SELL"
                    sr_confidence = -15
                
                # Trend detection
                if sma_20 > sma_50 and rsi > 50:
                    trend = "bullish"
                elif sma_20 < sma_50 and rsi < 50:
                    trend = "bearish"
                else:
                    trend = "neutral"
                
                # Signal berdasarkan multi-indikator + volume + S/R
                signal = "HOLD"
                confidence = 50
                base_confidence = 0
                
                # RSI logic
                if rsi < 30:
                    signal = "BUY"
                    base_confidence = 75
                elif rsi > 70:
                    signal = "SELL"
                    base_confidence = 75
                # MACD logic
                elif macd > macd_signal and trend == "bullish":
                    signal = "BUY"
                    base_confidence = 65
                elif macd < macd_signal and trend == "bearish":
                    signal = "SELL"
                    base_confidence = 65
                
                # Tambahkan volume dan S/R ke confidence
                final_confidence = base_confidence + volume_confidence + sr_confidence + bb_confidence
                final_confidence = max(30, min(90, final_confidence))
                
                # Override signal jika volume/SR kuat
                if volume_signal == "HIGH_VOLUME" and signal == "HOLD":
                    if base_confidence > 0:
                        signal = "BUY" if base_confidence > 50 else "SELL"
                
                weight = config["weight"]
                total_weight += weight
                
                if signal == "BUY":
                    weighted_buy += weight
                elif signal == "SELL":
                    weighted_sell += weight
                else:
                    weighted_neutral += weight
                
                timeframe_signals[tf_name] = {
                    "signal": signal,
                    "confidence": final_confidence,
                    "rsi": round(rsi, 1),
                    "trend": trend,
                    "macd": round(macd, 4),
                    "price": round(current_price, 2),
                    "volume_ratio": round(volume_ratio, 2),
            "guavy_indicators": guavy_indicators,
            "ai_pattern": ai_pattern if "ai_pattern" in locals() else None,
            "ai_override": ai_override if "ai_override" in locals() else False,
                    "support": round(nearest_support, 2),
                    "resistance": round(nearest_resistance, 2),
                    "atr": round(atr, 2),
                    "atr_percent": round(atr_percent, 2),
                    "bb_upper": round(upper_band, 2),
                    "bb_middle": round(middle_band, 2),
                    "bb_lower": round(lower_band, 2),
                    "bb_position": round(bb_position, 2)
                }
                
            except Exception as e:
                print(f"Error on {tf_name}: {e}")
                continue
        
        # Pilih AI Pattern terbaik dari semua timeframe (berdasarkan confidence)
        ai_pattern = None
        if hasattr(self, '_ai_patterns') and self._ai_patterns:
            # Pilih yang confidence tertinggi
            best = max(self._ai_patterns, key=lambda x: x.get('confidence', 0))
            ai_pattern = best
            # Bersihkan untuk analisis berikutnya
            delattr(self, '_ai_patterns')
        
        # Hitung support/resistance global dari semua timeframe
        if all_prices:
            global_support = np.percentile(all_prices, 30)
            global_resistance = np.percentile(all_prices, 70)
        else:
            global_support = latest_price * 0.97
            global_resistance = latest_price * 1.03
        
        # Final decision based on weighted voting + AI Pattern
        if total_weight > 0:
            if weighted_buy >= weighted_sell and weighted_buy >= weighted_neutral:
                final_signal = "BUY"
                final_confidence = int(50 + (weighted_buy / total_weight) * 40)
            elif weighted_sell >= weighted_buy and weighted_sell >= weighted_neutral:
                final_signal = "SELL"
                final_confidence = int(50 + (weighted_sell / total_weight) * 40)
            else:
                final_signal = "HOLD"
                final_confidence = 50
        else:
            final_signal = "HOLD"
            final_confidence = 50
        
        # AI Pattern override (jika confidence tinggi)
        if ai_pattern and ai_pattern.get('confidence', 0) >= 70:
            ai_signal = ai_pattern.get('signal')
            if ai_signal in ['BUY', 'SELL']:
                # Jika AI pattern sangat yakin, timbang dengan bobot 30%
                ai_weight = 30
                total_weight_with_ai = total_weight + ai_weight
                if final_confidence > 0:
                    weighted_final = (final_confidence * total_weight + ai_pattern.get('confidence', 50) * ai_weight) / total_weight_with_ai
                else:
                    weighted_final = ai_pattern.get('confidence', 50)
                
                if ai_signal == 'BUY':
                    final_signal = 'BUY'
                elif ai_signal == 'SELL':
                    final_signal = 'SELL'
                
                final_confidence = int(weighted_final)
                # Simpan informasi bahwa AI mempengaruhi
                ai_override = True
            else:
                ai_override = False
        else:
            ai_override = False
        
        # ========== TAMBAHAN UNTUK DYNAMIC STOP LOSS ==========
        avg_atr_percent = 1.5
        volume_ratio_avg = 1.0
        
        # Hitung rata-rata ATR dari semua timeframe
        if timeframe_signals:
            atr_vals = [tf.get("atr_percent", 0) for tf in timeframe_signals.values() if tf.get("atr_percent")]
            vol_vals = [tf.get("volume_ratio", 0) for tf in timeframe_signals.values() if tf.get("volume_ratio")]
            if atr_vals:
                avg_atr_percent = sum(atr_vals) / len(atr_vals)
            if vol_vals:
                volume_ratio_avg = sum(vol_vals) / len(vol_vals)
        
        if timeframe_signals:
            atr_values = []
            vol_ratios = []
            
            for tf_name, tf_data in timeframe_signals.items():
                if tf_data.get("atr_percent"):
                    atr_values.append(tf_data["atr_percent"])
                if tf_data.get("volume_ratio"):
                    vol_ratios.append(tf_data["volume_ratio"])
            
            if atr_values:
                avg_atr_percent = sum(atr_values) / len(atr_values)
            
            if vol_ratios:
                volume_ratio_avg = sum(vol_ratios) / len(vol_ratios)
        # ========== END TAMBAHAN ==========
        return {
            "agent": self.name,
            "signal": final_signal,
            "confidence": final_confidence,
            "trend": self._get_overall_trend(timeframe_signals),
            "rsi": self._get_average_rsi(timeframe_signals),
            "price": latest_price,
            "support": round(global_support, 2),
            "resistance": round(global_resistance, 2),
            "timeframes": timeframe_signals,
            "timestamp": datetime.now().isoformat(),
            "atr_percent": round(avg_atr_percent, 2),
            "volume_ratio": round(volume_ratio_avg, 2),
            "guavy_indicators": guavy_indicators,
            "ai_pattern": ai_pattern if "ai_pattern" in locals() else None,
            "ai_override": ai_override if "ai_override" in locals() else False,
        }
    
    def _get_overall_trend(self, timeframe_signals):
        bullish_count = sum(1 for tf in timeframe_signals.values() if tf.get("trend") == "bullish")
        bearish_count = sum(1 for tf in timeframe_signals.values() if tf.get("trend") == "bearish")
        if bullish_count > bearish_count:
            return "bullish"
        elif bearish_count > bullish_count:
            return "bearish"
        else:
            return "neutral"
    
    def _get_average_rsi(self, timeframe_signals):
        rsi_values = [tf.get("rsi", 50) for tf in timeframe_signals.values()]
        return round(sum(rsi_values) / len(rsi_values), 1) if rsi_values else 50
    
    def _calculate_rsi(self, prices, period=14):
        if len(prices) < period + 1:
            return 50.0
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        if len(prices) < slow:
            return 0, 0
        ema_fast = self._ema(prices, fast)
        ema_slow = self._ema(prices, slow)
        macd_line = ema_fast - ema_slow
        macd_signal = self._ema([macd_line], signal) if len([macd_line]) >= signal else macd_line
        return macd_line, macd_signal
    
    
    
    def calculate_bollinger(self, prices, period=20, std_dev=2):
        """Calculate Bollinger Bands untuk deteksi overbought/oversold"""
        if len(prices) < period:
            return 0, 0, 0
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, sma, lower

    def calculate_atr(self, high, low, close, period=14):
        """Calculate Average True Range (ATR) untuk dynamic stop loss"""
        if len(close) < period + 1:
            return 0
        tr = []
        for i in range(1, len(close)):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i-1])
            lc = abs(low[i] - close[i-1])
            tr.append(max(hl, hc, lc))
        return sum(tr[-period:]) / period if len(tr) >= period else 0


    async def _analyze_patterns_with_ai(self, prices, volumes, timeframe="1h"):
        """Analisis pola chart kompleks menggunakan Groq AI"""
        try:
            from groq import Groq
            import os
            from dotenv import load_dotenv
            import json
            import re
            
            load_dotenv('/home/ubuntu/groq_trading_bot/.env')
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                return None
            
            client = Groq(api_key=api_key)
            
            if len(prices) < 20:
                return None
            
            # Data harga terbaru
            recent_prices = prices[-50:] if len(prices) > 50 else prices
            recent_volumes = volumes[-50:] if len(volumes) > 50 else volumes
            
            price_high = max(recent_prices)
            price_low = min(recent_prices)
            price_current = recent_prices[-1]
            price_ma20 = sum(recent_prices[-20:]) / 20 if len(recent_prices) >= 20 else price_current
            price_change = ((price_current - recent_prices[0]) / recent_prices[0]) * 100 if recent_prices[0] > 0 else 0
            
            volume_avg = sum(recent_volumes[-20:]) / 20 if len(recent_volumes) >= 20 else 1
            volume_ratio = recent_volumes[-1] / volume_avg if volume_avg > 0 else 1
            
            prompt = f"""You are a professional technical analyst. Analyze the following BTC price data and identify chart patterns.

DATA:
Timeframe: {timeframe}
Current Price: ${price_current:,.0f}
24h Change: {price_change:.1f}%
24h High: ${price_high:,.0f}
24h Low: ${price_low:,.0f}
20-period MA: ${price_ma20:,.0f}
Volume Ratio (vs avg): {volume_ratio:.2f}x

INSTRUCTIONS:
1. Identify any of these patterns if present:
   - Head and Shoulders (bearish reversal)
   - Inverse Head and Shoulders (bullish reversal)
   - Double Top (bearish reversal)
   - Double Bottom (bullish reversal)
   - Bull Flag (continuation bullish)
   - Bear Flag (continuation bearish)
   - Ascending Triangle (bullish)
   - Descending Triangle (bearish)

2. Rate confidence based on pattern clarity

RESPOND WITH JSON ONLY (no other text):
{{
    "pattern": "pattern_name or none",
    "signal": "BUY/SELL/HOLD",
    "confidence": 0-100,
    "reason": "brief explanation of pattern detected"
}}"""

            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=300
            )
            
            text = response.choices[0].message.content
            match = re.search(r'\{[^{}]*\}', text)
            if match:
                result = json.loads(match.group())
                return {
                    "pattern": result.get("pattern", "none"),
                    "signal": result.get("signal", "HOLD"),
                    "confidence": result.get("confidence", 50),
                    "reason": result.get("reason", ""),
                    "ai_used": "groq-llama-3.1"
                }
        except Exception as e:
            print(f"AI pattern error: {e}")
        return None

    def _ema(self, data, period):
        if len(data) == 0:
            return 0
        multiplier = 2 / (period + 1)
        ema = data[0]
        for value in data[1:]:
            ema = (value - ema) * multiplier + ema
        return ema
