# 🤖 Multi AI Agent Trading Bot for KuCoin Futures

Multi-Agent Trading Bot untuk KuCoin Futures menggunakan 6 AI Agent dengan AI Orchestrator.

## Fitur Utama
- 6 AI Agent: Technical, Sentiment, News, Exchange, Whale, Risk
- AI Orchestrator: OpenRouter (Qwen) + Groq (Llama) fallback
- Auto-trade setiap 30 menit
- Reverse Trading dengan cooldown
- SL/TP Monitoring real-time
- Telegram Bot untuk kontrol dan notifikasi

## Instalasi
1. Clone repository
2. Copy `.env.example` ke `.env` dan isi API keys
3. `pip install -r requirements.txt`
4. `python3 main.py`

## API Keys Required
- Telegram Bot Token
- KuCoin Futures API
- OpenRouter API (gratis)
- Groq API (gratis)
- Arkham API (opsional)

## License
MIT
