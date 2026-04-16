#!/usr/bin/env python3
"""
Groq Orchestrator - Pure AI Decision Making
TANPA RULE, hanya analisa data mentah
"""

import os
import json
import re
import requests
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GroqOrchestrator:
    def __init__(self):
        # Load .env manually
        env_file = '/home/ubuntu/groq_trading_bot/.env'
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        os.environ[key] = value.strip()
        
        self.name = "AI Orchestrator"
        
        # OpenRouter (Primary)
        self.openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        self.openrouter_model = "openai/gpt-3.5-turbo"
        self.use_openrouter = bool(self.openrouter_api_key)
        
        # Groq (Fallback)
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        self.groq_client = None
        self.groq_model = "llama-3.1-8b-instant"
        
        if self.groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_key)
            except:
                pass
        
        print(f"🤖 Orchestrator: OpenRouter={'✅' if self.use_openrouter else '❌'}, Groq={'✅' if self.groq_client else '❌'}")

    def _call_openrouter(self, prompt):
        """Panggil OpenRouter API"""
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "Trading Bot"
                },
                json={
                    "model": self.openrouter_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 250
                },
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
        except Exception as e:
            print(f"OpenRouter error: {e}")
        return None

    def _call_groq(self, prompt):
        """Panggil Groq API (fallback)"""
        if not self.groq_client:
            return None
        try:
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=250
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Groq error: {e}")
        return None

    async def decide(self, technical, sentiment, news_social, exchange, whale, risk, current_price, has_position, last_action=None):
        """
        Pure AI Decision - TANPA RULE TAMBAHAN
        Hanya mengikuti risk agent untuk keamanan
        """
        
        # Hanya aturan keamanan dari risk agent
        if not risk.get('can_trade', True):
            return {
                "action": "HOLD",
                "confidence": 50,
                "reason": f"Risk agent blocks trading: {risk.get('reason', 'Unknown')}",
                "ai_used": "rule-based"
            }
        
        if has_position:
            return {
                "action": "HOLD",
                "confidence": 50,
                "reason": "Position already open",
                "ai_used": "rule-based"
            }
        
        # Prompt sederhana tanpa rule
        prompt = f"""Kamu adalah profesional crypto analisa. 

⚠️ PENTING: Pertimbangkan SEMUA analisa dari semua agent di bawah ini. JANGAN mengabaikan agent manapun.

DATA DARI SEMUA AGENT:

1. TECHNICAL AGENT:
   Signal: {technical.get('signal', 'HOLD')}
   Confidence: {technical.get('confidence', 50)}%
   RSI: {technical.get('rsi', 'N/A')}
   Trend: {technical.get('trend', 'N/A')}
   Volume Ratio: {technical.get('volume_ratio', 'N/A')}x

2. SENTIMENT AGENT:
   Signal: {sentiment.get('signal', 'HOLD')}
   Confidence: {sentiment.get('confidence', 50)}%
   Fear & Greed: {sentiment.get('fear_greed', {}).get('value', 'N/A')} ({sentiment.get('fear_greed', {}).get('classification', 'N/A')})

3. NEWS AGENT:
   Signal: {news_social.get('signal', 'HOLD')}
   Confidence: {news_social.get('confidence', 50)}%
   Headlines: {news_social.get('headlines_count', 0)}

4. EXCHANGE AGENT:
   Signal: {exchange.get('signal', 'HOLD')}
   Confidence: {exchange.get('confidence', 50)}%
   Volume 24h: {exchange.get('volume_24h', 0):,.0f} BTC
   Volume Surge: {exchange.get('volume_surge', 'N/A')}

5. WHALE AGENT:
   Signal: {whale.get('signal', 'HOLD')}
   Confidence: {whale.get('confidence', 50)}%
   Net Flow: ${whale.get('net_flow_m', 0):+.1f}M

6. RISK AGENT:
   Can Trade: {risk.get('can_trade', True)}
   Reason: {risk.get('reason', 'OK')}

HARGA SAAT INI: ${current_price:,.2f}

TUGAS:
1. Pertimbangkan SEMUA analisa dari 6 agent di atas
2. Jangan mengabaikan agent manapun
4. Keputusan harus berdasarkan KONSENSUS dari semua agent
5. Output HANYA valid JSON: {{"action": "BUY/SELL/HOLD", "confidence": 0-100, "reason": "alasan singkat berdasarkan semua agent"}}"""

        # Coba OpenRouter dulu
        ai_response = self._call_openrouter(prompt)
        ai_used = "openrouter"
        
        # Fallback ke Groq
        if not ai_response:
            ai_response = self._call_groq(prompt)
            ai_used = "groq"
        
        # Parse response
        if ai_response:
            match = re.search(r'\{[^{}]*\}', ai_response)
            if match:
                try:
                    result = json.loads(match.group())
                    result['ai_used'] = ai_used
                    return result
                except:
                    pass
        
        # Fallback jika AI gagal
        return {
            "action": "HOLD",
            "confidence": 50,
            "reason": "AI analysis failed",
            "ai_used": "fallback"
        }


if __name__ == "__main__":
    import asyncio
    async def test():
        groq = GroqOrchestrator()
        
        # Test data
        technical = {"signal": "HOLD", "confidence": 50, "rsi": 41.2, "trend": "neutral", "volume_ratio": 1.2}
        sentiment = {"signal": "HOLD", "confidence": 50, "fear_greed": {"value": 23, "classification": "Extreme Fear"}}
        news_social = {"signal": "SELL", "confidence": 80, "headlines_count": 50}
        exchange = {"signal": "HOLD", "confidence": 50, "volume_24h": 12500, "volume_surge": "high"}
        whale = {"signal": "SELL", "confidence": 70, "net_flow_m": -137}
        risk = {"can_trade": True, "reason": "OK"}
        
        result = await groq.decide(
            technical=technical, sentiment=sentiment, news_social=news_social,
            exchange=exchange, whale=whale, risk=risk,
            current_price=75000, has_position=False, last_action=None
        )
        
        print(f"\n🎯 AI DECISION (Pure AI - No Rules):")
        print(f"   Action: {result.get('action')}")
        print(f"   Confidence: {result.get('confidence')}%")
        print(f"   Reason: {result.get('reason')}")
        print(f"   AI Used: {result.get('ai_used')}")
    
    asyncio.run(test())
