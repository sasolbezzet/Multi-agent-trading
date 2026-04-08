import requests
import os
from datetime import datetime

class SentimentAgent:
    def __init__(self):
        self.name = "Sentiment Analyst"
        self.guavy_api_key = os.getenv('GUAVY_API_KEY')
    
    async def analyze(self):
        """Analisis sentimen dari multiple sumber (Fear & Greed + Guavy + Free Crypto News + Alpha Vantage)"""
        
        # 1. Fear & Greed dari alternative.me
        fg_data = await self._get_fear_greed()
        
        # 2. Guavy API (AI-powered sentiment)
        guavy_data = await self._get_guavy_sentiment()
        
        # 3. Free Crypto News API (no API key)
        free_news = await self._get_free_crypto_news()
        
        # 4. Alpha Vantage (backup)
        alpha_sentiment = await self._get_alpha_sentiment()
        
        # Gabungkan semua sinyal
        combined = self._combine_signals(fg_data, guavy_data, free_news, alpha_sentiment)
        
        return {
            "agent": self.name,
            "signal": combined["signal"],
            "confidence": combined["confidence"],
            "fear_greed": fg_data,
            "guavy": guavy_data,
            "guavy_sentiment": guavy_data,
            "free_news_sentiment": free_news,
            "alpha_sentiment": alpha_sentiment,
            "reason": combined["reason"],
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_fear_greed(self):
        """Fear & Greed Index dari alternative.me"""
        try:
            resp = requests.get("https://api.alternative.me/fng/", timeout=10)
            data = resp.json()
            value = int(data['data'][0]['value'])
            classification = data['data'][0]['value_classification']
            
            if value < 25:
                signal = "BUY"
                confidence = 85
            elif value < 40:
                signal = "BUY"
                confidence = 70
            elif value > 75:
                signal = "SELL"
                confidence = 85
            elif value > 60:
                signal = "SELL"
                confidence = 70
            else:
                signal = "HOLD"
                confidence = 50
            
            return {
                "value": value,
                "classification": classification,
                "signal": signal,
                "confidence": confidence
            }
        except:
            return {"value": 50, "classification": "Neutral", "signal": "HOLD", "confidence": 50}
    
    async def _get_guavy_sentiment(self):
        """Guavy API - AI-powered sentiment (5,000 request/bulan gratis)"""
        if not self.guavy_api_key:
            return {"signal": "HOLD", "confidence": 50, "score": 0}
        
        try:
            url = "https://data.guavy.com/api/v1/sentiment"
            headers = {"X-API-Key": self.guavy_api_key}
            params = {"asset": "BTC", "limit": 1}
            
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                signal_label = data.get('signal', 'neutral')
                sentiment_score = data.get('sentiment_score', 0.5)
                
                if signal_label == 'bullish':
                    signal = "BUY"
                    confidence = int(sentiment_score * 100)
                elif signal_label == 'bearish':
                    signal = "SELL"
                    confidence = int((1 - sentiment_score) * 100)
                else:
                    signal = "HOLD"
                    confidence = 50
                
                return {
                    "signal": signal,
                    "confidence": min(confidence, 85),
                    "score": sentiment_score,
                    "label": signal_label,
                    "source": "Guavy"
                }
        except Exception as e:
            print(f"Guavy error: {e}")
        
        return {"signal": "HOLD", "confidence": 50, "score": 0}
    
    async def _get_free_crypto_news(self):
        """Free Crypto News API (no API key required)"""
        try:
            # Sentiment untuk Bitcoin
            url = "https://cryptocurrency.cv/api/ai/sentiment?asset=BTC"
            resp = requests.get(url, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                label = data.get('label', 'Neutral')
                score = data.get('score', 0.5)
                
                if label == 'Bullish':
                    signal = "BUY"
                    confidence = int(score * 100)
                elif label == 'Bearish':
                    signal = "SELL"
                    confidence = int(score * 100)
                else:
                    signal = "HOLD"
                    confidence = 50
                
                return {
                    "signal": signal,
                    "confidence": min(confidence, 85),
                    "score": score,
                    "label": label,
                    "source": "Free Crypto News API"
                }
        except Exception as e:
            print(f"Free Crypto News error: {e}")
        
        return {"signal": "HOLD", "confidence": 50, "score": 0}
    
    async def _get_alpha_sentiment(self):
        """Alpha Vantage News Sentiment"""
        try:
            api_key = os.getenv('ALPHA_VANTAGE_KEY')
            if not api_key:
                return {"signal": "HOLD", "confidence": 50, "score": 0}
            
            url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers=BTC&apikey={api_key}&limit=5"
            resp = requests.get(url, timeout=15)
            
            if resp.status_code == 200:
                data = resp.json()
                if 'feed' in data and len(data['feed']) > 0:
                    sentiments = []
                    for article in data['feed'][:5]:
                        score = article.get('overall_sentiment_score', 0)
                        sentiments.append(score)
                    
                    avg_score = sum(sentiments) / len(sentiments)
                    
                    if avg_score > 0.2:
                        signal = "BUY"
                        confidence = 70
                    elif avg_score > 0.1:
                        signal = "BUY"
                        confidence = 60
                    elif avg_score < -0.2:
                        signal = "SELL"
                        confidence = 70
                    elif avg_score < -0.1:
                        signal = "SELL"
                        confidence = 60
                    else:
                        signal = "HOLD"
                        confidence = 50
                    
                    return {
                        "signal": signal,
                        "confidence": confidence,
                        "score": round(avg_score, 3)
                    }
        except:
            pass
        
        return {"signal": "HOLD", "confidence": 50, "score": 0}
    
    def _combine_signals(self, fg, guavy, free_news, alpha):
        """Menggabungkan semua sinyal sentimen"""
        signals = {"BUY": 0, "SELL": 0}
        
        # Fear & Greed (bobot 3)
        fg_signal = fg.get('signal', 'HOLD')
        if fg_signal in signals:
            signals[fg_signal] += 3
        
        # Guavy AI (bobot 2)
        guavy_signal = guavy.get('signal', 'HOLD')
        if guavy_signal in signals:
            signals[guavy_signal] += 2
        
        # Free Crypto News (bobot 2)
        free_signal = free_news.get('signal', 'HOLD')
        if free_signal in signals:
            signals[free_signal] += 2
        
        # Alpha Vantage (bobot 1)
        alpha_signal = alpha.get('signal', 'HOLD')
        if alpha_signal in signals:
            signals[alpha_signal] += 1
        
        total_buy = signals.get('BUY', 0)
        total_sell = signals.get('SELL', 0)
        
        if total_buy >= 5:
            return {
                "signal": "BUY",
                "confidence": 85,
                "reason": f"Strong bullish: F&G={fg.get('value')}, Guavy={guavy.get('label', 'N/A')}, News={free_news.get('score', 0):+.2f}"
            }
        elif total_sell >= 5:
            return {
                "signal": "SELL",
                "confidence": 85,
                "reason": f"Strong bearish: F&G={fg.get('value')}, Guavy={guavy.get('label', 'N/A')}, News={free_news.get('score', 0):+.2f}"
            }
        elif total_buy >= 3:
            return {
                "signal": "BUY",
                "confidence": 65,
                "reason": f"Bullish: F&G={fg.get('value')}, Guavy={guavy.get('label', 'N/A')}"
            }
        elif total_sell >= 3:
            return {
                "signal": "SELL",
                "confidence": 65,
                "reason": f"Bearish: F&G={fg.get('value')}, Guavy={guavy.get('label', 'N/A')}"
            }
        else:
            return {
                "signal": "HOLD",
                "confidence": 50,
                "reason": f"Mixed/neutral: F&G={fg.get('value')}"
            }

    async def _get_guavy_sentiment(self):
        """Ambil data sentimen dari Guavy API"""
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
                return {"signal": "HOLD", "net_score": 0}
            
            url = "https://data.guavy.com/api/v1/sentiment/get-sentiment-history/BTC"
            headers = {"Authorization": f"Bearer {api_key}"}
            params = {"limit": 1}
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                sentiment = data.get('sentiment', [])
                if sentiment:
                    s = sentiment[0]
                    positive = s.get('positive', 0)
                    negative = s.get('negative', 0)
                    total = s.get('total', 1)
                    net_score = ((positive - negative) / total) * 100
                    
                    if net_score > 20:
                        signal = "BUY"
                    elif net_score < -20:
                        signal = "SELL"
                    else:
                        signal = "HOLD"
                    
                    return {"signal": signal, "net_score": round(net_score, 1), "positive": positive, "negative": negative}
        except Exception as e:
            print(f"Guavy error: {e}")
        return {"signal": "HOLD", "net_score": 0}
