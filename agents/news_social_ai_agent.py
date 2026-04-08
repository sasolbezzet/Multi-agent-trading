import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from groq import Groq
import os
import asyncio
import time
import json
import re

class NewsSocialAIAgent:
    def __init__(self):
        self.name = "News & Social Analyst (AI)"
        # Load API key manually
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
    
    async def _get_rss_headlines(self):
        all_headlines = []
        for name, url in self.rss_sources:
            try:
                resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    try:
                        root = ET.fromstring(resp.content)
                        for item in root.findall('.//item')[:3]:
                            title = item.find('title')
                            if title is not None and title.text:
                                all_headlines.append(title.text)
                    except:
                        continue
            except:
                continue
        return all_headlines
    
    async def _analyze_with_groq(self, headlines):
        if not headlines:
            return {"signal": "HOLD", "confidence": 50, "reason": "No news available", "score": 0}
        
        news_text = "\n".join([f"- {h}" for h in headlines[:15]])
        
        prompt = f"""Analyze these crypto news headlines and determine sentiment.

HEADLINES:
{news_text}

Respond with JSON only:
{{"signal": "BUY/SELL/HOLD", "confidence": 0-100, "sentiment_score": -1 to +1, "reason": "brief"}}"""
        
        try:
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200
            )
            text = response.choices[0].message.content
            match = re.search(r'\{[^{}]*\}', text)
            if match:
                result = json.loads(match.group())
                return {
                    "signal": result.get("signal", "HOLD"),
                    "confidence": result.get("confidence", 50),
                    "score": result.get("sentiment_score", 0),
                    "reason": result.get("reason", "AI analysis completed"),
                    "ai_used": "groq-llama-3.1"
                }
        except Exception as e:
            print(f"Groq AI error: {e}")
        
        return {"signal": "HOLD", "confidence": 50, "score": 0, "reason": "AI analysis failed", "ai_used": "fallback"}
    
    async def _get_geopolitical_risk(self):
        current_time = time.time()
        if self._geo_cache is not None and (current_time - self._geo_cache_time) < 3600:
            return self._geo_cache
        
        try:
            from gdeltdoc import GdeltDoc, Filters
            def fetch():
                gd = GdeltDoc()
                f = Filters(keyword="geopolitical OR war OR conflict", timespan="6h", num_records=30)
                return gd.article_search(f)
            articles = await asyncio.to_thread(fetch)
            result = {"signal": "HOLD", "confidence": 50, "risk_score": 0, "reason": "No geopolitical news"}
            self._geo_cache = result
            self._geo_cache_time = time.time()
            return result
        except:
            return {"signal": "HOLD", "confidence": 50, "risk_score": 0, "reason": "Unavailable"}
    
    async def analyze(self):
        headlines = await self._get_rss_headlines()
        ai_result = await self._analyze_with_groq(headlines)
        geo_risk = await self._get_geopolitical_risk()
        
        if geo_risk.get('signal') == 'SELL' and geo_risk.get('risk_score', 0) > 50:
            final_signal = 'SELL'
            final_confidence = max(ai_result.get('confidence', 50), geo_risk.get('confidence', 50))
            reason = f"Geopolitical override: {geo_risk.get('reason')}"
        else:
            final_signal = ai_result.get('signal', 'HOLD')
            final_confidence = ai_result.get('confidence', 50)
            reason = f"AI Sentiment: {ai_result.get('reason', 'N/A')}"
        
        return {
            "agent": self.name,
            "signal": final_signal,
            "confidence": final_confidence,
            "ai_analysis": ai_result,
            "geopolitical": geo_risk,
            "articles_count": len(headlines),
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
