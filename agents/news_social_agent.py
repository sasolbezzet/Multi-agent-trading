import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from groq import Groq
import os
import asyncio
import time
import json
import re

class NewsSocialAgent:
    def __init__(self):
        self.name = "News & Social Analyst (AI)"
        env_file = '/home/ubuntu/groq_trading_bot/.env'
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.groq_model = "llama-3.1-8b-instant"
        
        self._geo_cache = None
        self._geo_cache_time = 0
        
        self.rss_sources = [
            ("CoinTelegraph", "https://cointelegraph.com/rss"),
            ("Bitcoin.com", "https://news.bitcoin.com/feed/"),
            ("ZyCrypto", "https://zycrypto.com/feed/"),
            ("CryptoPotato", "https://cryptopotato.com/feed/"),
            ("NewsBTC", "https://www.newsbtc.com/feed/"),
            ("Bitcoinist", "https://bitcoinist.com/feed/"),
            ("CryptoNews", "https://cryptonews.com/feed/"),
            ("Decrypt", "https://decrypt.co/feed"),
        ]
    


    async def _get_guavy_briefs(self, symbol="BTC", limit=5):
        """Ambil berita terbaru dari Guavy API"""
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
                return []
            
            url = f"https://data.guavy.com/api/v1/newsroom/get-recent-briefs/{symbol}"
            headers = {"Authorization": f"Bearer {api_key}"}
            params = {"limit": limit}
            
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                briefs = data.get('briefs', [])
                return [f"[Guavy] {b.get('body', '')[:200]}" for b in briefs if b.get('body')]
        except Exception as e:
            print(f"Guavy briefs error: {e}")
        return []

    async def _get_rss_headlines(self):
        all_headlines = []
        
        # 1. RSS Feeds
        for name, url in self.rss_sources:
            try:
                resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    try:
                        root = ET.fromstring(resp.content)
                        for item in root.findall('.//item')[:3]:
                            title = item.find('title')
                            if title is not None and title.text:
                                all_headlines.append(f"[RSS] {title.text}")
                    except:
                        continue
            except:
                continue
        
        # 2. NewsAPI (jika ada key)
        newsapi_key = os.getenv('NEWSAPI_KEY')
        if newsapi_key:
            try:
                url = "https://newsapi.org/v2/everything"
                params = {"q": "cryptocurrency", "apiKey": newsapi_key, "pageSize": 5, "language": "en"}
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for art in data.get('articles', []):
                        title = art.get('title')
                        if title:
                            all_headlines.append(f"[NewsAPI] {title}")
            except:
                pass
        
        # 3. GNews (jika ada key)
        gnews_key = os.getenv('GNEWS_KEY')
        if gnews_key:
            try:
                url = "https://gnews.io/api/v4/search"
                params = {"q": "cryptocurrency", "apikey": gnews_key, "max": 5, "lang": "en"}
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for art in data.get('articles', []):
                        title = art.get('title')
                        if title:
                            all_headlines.append(f"[GNews] {title}")
            except:
                pass
        
        # 4. Guavy Briefs (berita terbaru)
        guavy_briefs = await self._get_guavy_briefs("BTC", 5)
        for b in guavy_briefs:
            all_headlines.append(b)
        
        return all_headlines
    
    async def _get_geopolitical_risk(self):
        current_time = time.time()
        if self._geo_cache is not None and (current_time - self._geo_cache_time) < 3600:
            return self._geo_cache
        
        result = {"signal": "HOLD", "confidence": 50, "risk_score": 0, "reason": "No geopolitical news"}
        self._geo_cache = result
        self._geo_cache_time = time.time()
        return result
    
    async def _analyze_with_groq(self, headlines):
        if not headlines:
            return {"signal": "HOLD", "confidence": 50, "reason": "No news", "score": 0}
        
        # Ambil 15 headline pertama
        news_text = "\n".join([f"- {h}" for h in headlines[:15]])
        
        prompt = f"""You are a crypto market analyst. Analyze these news headlines and give sentiment.

News:
{news_text}

Return ONLY valid JSON:
{{"signal": "BUY/SELL/HOLD", "confidence": 0-100, "sentiment_score": -1 to 1, "key_themes": ["theme"], "reason": "brief analysis"}}"""
        
        try:
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=300
            )
            text = response.choices[0].message.content
            # Extract JSON
            match = re.search(r'\{[^{}]*\}', text)
            if match:
                result = json.loads(match.group())
                return {
                    "signal": result.get("signal", "HOLD"),
                    "confidence": result.get("confidence", 50),
                    "score": result.get("sentiment_score", 0),
                    "key_themes": result.get("key_themes", []),
                    "reason": result.get("reason", "AI analysis"),
                    "ai_used": "groq-llama-3.1"
                }
        except Exception as e:
            print(f"Groq error: {e}")
        
        return {"signal": "HOLD", "confidence": 50, "score": 0, "reason": "Analysis failed", "ai_used": "fallback"}
    
    async def analyze(self):
        headlines = await self._get_rss_headlines()
        geo_risk = await self._get_geopolitical_risk()
        ai_result = await self._analyze_with_groq(headlines)
        
        return {
            "agent": self.name,
            "signal": ai_result.get("signal", "HOLD"),
            "confidence": ai_result.get("confidence", 50),
            "ai_analysis": ai_result,
            "geopolitical": geo_risk,
            "headlines_count": len(headlines),
            "reason": ai_result.get("reason", "AI analysis"),
            "timestamp": datetime.now().isoformat()
        }
