import json
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/ubuntu/groq_trading_bot/.env")
from groq import Groq
from openai import OpenAI
from backtest_metrics import BacktestMetrics

class GroqOrchestrator:


    async def _get_guavy_scorecard(self):
        """Ambil scorecard dari Guavy API untuk BTC"""
        try:
            import requests
            import os
            
            api_key = os.getenv('GUAVY_API_KEY')
            if not api_key:
                return None
            
            url = "https://data.guavy.com/api/v1/instruments/scorecard/BTC"
            headers = {"Authorization": f"Bearer {api_key}"}
            
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "action": data.get('action'),
                    "score": data.get('score'),
                    "profit_percentage": data.get('percentage_profit'),
                    "in_trade": data.get('in_trade'),
                    "strategy": data.get('strategy'),
                    "source": "Guavy"
                }
        except Exception as e:
            print(f"Guavy scorecard error: {e}")
        return None

    def __init__(self):
        # Groq sebagai fallback
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.groq_model = "llama-3.1-8b-instant"
        
        # OpenRouter (Qwen)
        self.openrouter_key = os.getenv('OPENROUTER_API_KEY')
        if self.openrouter_key:
            self.openrouter_client = OpenAI(
                api_key=self.openrouter_key,
                base_url="https://openrouter.ai/api/v1"
            )
            self.use_qwen = True
        else:
            self.use_qwen = False
        
        # Dapatkan metrik backtesting
        self.backtest_metrics = BacktestMetrics()
        self.last_metrics = None
    
    async def decide(self, technical, sentiment, news_social, exchange, whale, risk, current_price, has_position, last_action=None):
        # EARLY VALIDATION: Jika risk agent tidak mengizinkan trade
        if not risk.get('can_trade', True):
            return {"action": "HOLD", "confidence": 50, "reason": "Risk agent blocks trading", "ai_used": "rule-based"}
        
        # EARLY VALIDATION: Jika sudah ada posisi, jangan BUY/SELL
        if has_position:
            return {"action": "HOLD", "confidence": 50, "reason": "Position already open, waiting for close", "ai_used": "rule-based"}
        
        # Dapatkan metrik backtesting terbaru
        try:
            metrics = self.backtest_metrics.get_recent_performance(7)
            accuracy = self.backtest_metrics.get_signal_accuracy()
        except:
            metrics = None
            accuracy = None
        
        # Simpan untuk digunakan dalam prompt
        backtest_info = ""
        if metrics:
            backtest_info = f"""
=== BACKTESTING METRICS (Last 7 days) ===
Total Return: {metrics['total_return']:+.2f}%
Win Rate: {metrics['win_rate']}%
Total Trades: {metrics['total_trades']}
Profitability: {'PROFITABLE' if metrics['is_profitable'] else 'NOT PROFITABLE'}
Win Rate Status: {'GOOD (>50%)' if metrics['is_good_win_rate'] else 'POOR (<50%)'}
"""
        
        if accuracy:
            backtest_info += f"""
=== HISTORICAL ACCURACY ===
Avg Return (1-30 days): {accuracy['avg_return']:+.2f}%
Avg Win Rate: {accuracy['avg_win_rate']}%
Trend: {accuracy['trend']}
"""
        
        prompt = f"""You are a crypto trading AI. Based on 6 agents and BACKTESTING RESULTS below, decide BUY/SELL/HOLD.

BTC Price: ${current_price}
{backtest_info}

=== TECHNICAL AGENT ===
Signal: {technical.get('signal')} ({technical.get('confidence')}%)
RSI: {technical.get('rsi', 50)} | Trend: {technical.get('trend', 'neutral')}

=== SENTIMENT AGENT ===
Signal: {sentiment.get('signal')} ({sentiment.get('confidence')}%)
Fear & Greed: {sentiment.get('fear_greed', 50)}

=== NEWS & SOCIAL AGENT ===
Signal: {news_social.get('signal')} ({news_social.get('confidence')}%)

=== EXCHANGE AGENT ===
Signal: {exchange.get('signal')} ({exchange.get('confidence')}%)

=== WHALE AGENT ===
Signal: {whale.get('signal')} ({whale.get('confidence')}%)
Reason: {whale.get('reason', '')[:100]}

=== RISK AGENT ===
Can Trade: {risk.get('can_trade', True)}
Risk Score: {risk.get('risk_score', 0)}/100
Min Confidence Required: {risk.get('min_confidence_required', 60)}%

=== STATUS ===
Has Position: {has_position}
Last Action: {last_action if last_action else 'None'}

=== BACKTESTING RULES ===
1. If backtesting shows POOR performance (<40% win rate in last 7 days) → BE MORE CONSERVATIVE (lower confidence threshold)
2. If backtesting shows PROFITABLE (>5% return in last 7 days) → CAN BE MORE AGGRESSIVE
3. If historical accuracy is DECLINING → REDUCE position size or HOLD
4. If backtesting has NO DATA (new bot) → Use default rules

RULES:
1. If Risk Agent says cannot trade → HOLD
2. If confidence < min_confidence_required → HOLD
3. If has position True and new signal opposite → CLOSE_ONLY
4. Otherwise, follow majority vote from all 6 agents

Respond with JSON only:
{{"action": "BUY/SELL/HOLD/CLOSE_ONLY", "confidence": 0-100, "reason": "brief including backtesting consideration"}}"""

        # Try Qwen first
        if self.use_qwen:
            try:
                response = self.openrouter_client.chat.completions.create(
                    model="qwen/qwen3.6-plus:free",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=250,
                    extra_headers={"HTTP-Referer": "http://localhost", "X-Title": "Trading Bot"}
                )
                text = response.choices[0].message.content
                match = re.search(r'\{[^{}]*\}', text)
                if match:
                    result = json.loads(match.group())
                    result['ai_used'] = 'qwen-3.6-plus'
                    result['backtest_considered'] = True
                    return result
            except Exception as e:
                print(f"Qwen error: {e}")
        
        # Fallback to Groq
        try:
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=250
            )
            text = response.choices[0].message.content
            match = re.search(r'\{[^{}]*\}', text)
            if match:
                result = json.loads(match.group())
                result['ai_used'] = 'groq-llama-3.1'
                result['backtest_considered'] = True
                return result
        except Exception as e:
            print(f"Groq error: {e}")
        
        return {"action": "HOLD", "confidence": 50, "reason": "Fallback", "ai_used": "fallback", "backtest_considered": False}
