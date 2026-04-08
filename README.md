
# 🤖 Multi AI Agent Trading Bot for KuCoin Futures

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## 📌 Overview

**Multi-Agent Trading Bot** adalah sistem trading otomatis untuk **KuCoin Futures** yang menggunakan **6 AI Agent** berbeda yang bekerja sama, dipandu oleh **AI Orchestrator (Qwen 3.6 Plus / Groq Llama 3.1)** untuk mengambil keputusan trading BUY/SELL/HOLD.

---

## 🏗️ Arsitektur Multi-Agent

```

┌─────────────────────────────────────────────────────────────────────────┐
│                         TELEGRAM INTERFACE                              │
│                   (User Commands & Notifications)                        │
└─────────────────────────────────┬───────────────────────────────────────┘
│
┌─────────────────────────────────▼───────────────────────────────────────┐
│                         AI ORCHESTRATOR                                  │
│              PRIMARY: Qwen 3.6 Plus (OpenRouter)                         │
│              FALLBACK: Groq Llama 3.1 8B                                 │
└─────────────────────────────────┬───────────────────────────────────────┘
│
┌─────────────────────────┼─────────────────────────┐
│                         │                         │
┌───────▼───────┐         ┌───────▼───────┐         ┌───────▼───────┐
│  TECHNICAL    │         │  SENTIMENT    │         │    NEWS       │
│    AGENT      │         │    AGENT      │         │    AGENT      │
│ (Multi-TF,    │         │ (Fear & Greed)│         │ (RSS Feeds)   │
│  RSI, MACD,   │         │               │         │               │
│  ATR, BB)     │         │               │         │               │
└───────┬───────┘         └───────┬───────┘         └───────┬───────┘
│                         │                         │
┌───────▼───────┐         ┌───────▼───────┐         ┌───────▼───────┐
│   EXCHANGE    │         │    WHALE      │         │    RISK       │
│    AGENT      │         │    AGENT      │         │    AGENT      │
│ (Funding Rate,│         │ (Arkham API + │         │ (Dynamic SL,  │
│  Order Book)  │         │  On-Chain)    │         │  Balance)     │
└───────────────┘         └───────────────┘         └───────────────┘

```

---

## 🤖 6 AGENT & SUMBER DATA

| Agent | Sumber Data | Fitur |
|-------|-------------|-------|
| 📊 **Technical** | Yahoo Finance | Multi-timeframe (15m,1h,4h,1d), RSI, MACD, SMA, Volume Analysis, Support/Resistance, ATR, Bollinger Bands |
| 📰 **Sentiment** | Alternative.me | Fear & Greed Index |
| 📱 **News/Social** | 8+ RSS Feeds | CoinTelegraph, Bitcoin.com, ZyCrypto, CryptoPotato, NewsBTC, Bitcoinist, CryptoNews, Decrypt |
| 💱 **Exchange** | Binance, Bybit, OKX, Kraken, BitMEX, Gate.io, MEXC | Funding Rate (8 exchange), Order Book Depth, Bid/Ask Ratio |
| 🐋 **Whale** | Arkham API + On-Chain GitHub | Large transfers, top holders, exchange netflow, whale ratio, miner position |
| 🛡️ **Risk** | KuCoin API | Dynamic Stop Loss (ATR-based), Balance check, SL/TP monitoring |

---

## 🔄 ALUR KERJA TRADING (DARI AWAL SAMPAI AKHIR)

```

┌─────────────────────────────────────────────────────────────────────────┐
│ 1. STARTUP                                                              │
│    • Load environment variables (.env)                                  │
│    • Initialize 6 Agents + AI Orchestrator + KuCoin API                 │
│    • Setup Telegram Bot (command handlers, callback queries)            │
│    • Start Scheduler (auto-analysis setiap 1 jam)                       │
│    • Start Background Monitoring (SL/TP setiap 10 detik)                │
│    • Start Hourly Notification (setiap jam ke Telegram)                 │
└─────────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. ANALISIS MULTI-AGENT (Setiap 1 Jam)                                  │
│                                                                         │
│   📊 Technical Agent  → RSI, MACD, Trend, ATR, Bollinger Bands          │
│   📰 Sentiment Agent  → Fear & Greed Index                              │
│   📱 News Agent       → 8 RSS feeds → AI sentiment analysis             │
│   💱 Exchange Agent   → Funding rate (8 exchange) + Order book depth    │
│   🐋 Whale Agent      → Arkham transfers + On-chain netflow/MPI         │
│   🛡️ Risk Agent       → Balance check, dynamic SL based on ATR          │
└─────────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. AI ORCHESTRATOR (Qwen 3.6 Plus / Groq Fallback)                      │
│                                                                         │
│   Input: 6 sinyal dari agent + price + posisi status                    │
│   Process: LLM menggabungkan semua sinyal dengan bobot implisit         │
│   Output: JSON {action: "BUY/SELL/HOLD/CLOSE_ONLY", confidence, reason} │
└─────────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. EKSEKUSI TRADING                                                     │
│                                                                         │
│   IF action in ['BUY','SELL'] AND no position AND risk.can_trade:       │
│       • Hitung dynamic stop loss (1.5x - 2x ATR, min 0.8%, max 3%)      │
│       • place_order(side, size=1, symbol)                               │
│       • Kirim notifikasi ke Telegram                                    │
│                                                                         │
│   IF has_position AND new signal opposite:                              │
│       • Close position                                                   │
│       • Open opposite position (reverse trading)                        │
│       • Kirim notifikasi ke Telegram                                    │
└─────────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. MONITORING SL/TP (Real-time setiap 10 detik)                         │
│                                                                         │
│   • Cek posisi saat ini                                                 │
│   • IF price <= SL (1.5x ATR dari entry) → CLOSE otomatis               │
│   • IF price >= TP (3% dari entry) → CLOSE otomatis                     │
│   • Kirim notifikasi ke Telegram jika kena SL/TP                        │
└─────────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. NOTIFIKASI TELEGRAM (Setiap Event)                                   │
│                                                                         │
│   • ⏰ HOURLY UPDATE → Setiap jam (01:00, 02:00, dst)                    │
│   • 🚀 AUTO TRADE → Saat eksekusi BUY/SELL                              │
│   • 🔴 STOP LOSS HIT → Saat SL kena                                     │
│   • 🎯 TAKE PROFIT HIT → Saat TP kena                                   │
│   • 🔄 REVERSE TRADING → Saat sinyal berlawanan                         │
│   • ❌ CANNOT TRADE → Saat balance tidak cukup atau posisi terbuka       │
└─────────────────────────────────────────────────────────────────────────┘

```

---

## 📦 INSTALASI

### 1. Clone Repository

```bash
git clone https://github.com/sasolbezzet/Multi-agent-trading.git
cd Multi-agent-trading
```

2. Setup Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# atau .\venv\Scripts\activate  # Windows
```

3. Install Dependencies

```bash
pip install -r requirements.txt
```

4. Konfigurasi Environment

```bash
cp .env.example .env
nano .env  # isi dengan API keys Anda
```

Daftar API Keys yang diperlukan:

API Keperluan Cara Dapat

TELEGRAM_BOT_TOKEN Bot Telegram @BotFather di Telegram

OPENROUTER_API_KEY AI Primary (Qwen) openrouter.ai (gratis)

GROQ_API_KEY AI Fallback (Llama) console.groq.com (gratis)

KUCOIN_API_KEY Trading Futures kucoin.com
KUCOIN_API_SECRET Trading Futures kucoin.com
KUCOIN_API_PASSPHRASE Trading Futures kucoin.com

ARKHAM_API_KEY Whale Tracking arkhamintelligence.com

5. Jalankan Bot

```bash
python3 main.py
```

6. Auto-Restart dengan Supervisor (Linux)

```bash
sudo apt install supervisor -y
sudo bash -c 'cat > /etc/supervisor/conf.d/groq-bot.conf << EOF
[program:groq-bot]
command=/home/ubuntu/Multi-agent-trading/venv/bin/python3 /home/ubuntu/Multi-agent-trading/main.py
directory=/home/ubuntu/Multi-agent-trading
user=ubuntu
autostart=true
autorestart=true
startretries=3
restartsecs=10
stderr_logfile=/home/ubuntu/Multi-agent-trading/logs/err.log
stdout_logfile=/home/ubuntu/Multi-agent-trading/logs/out.log
EOF'

sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start groq-bot
```

---

🎮 PERINTAH TELEGRAM

Tombol Fungsi
📊 MARKET STATUS Lihat semua sinyal 6 agent + posisi

🔍 FORCE SIGNAL Analisis real-time dengan 6 agent

💰 BALANCE Cek saldo KuCoin

📈 POSITION Detail posisi aktif

🔴 CLOSE POSITION Tutup posisi manual

🟢 AUTO ON Aktifkan auto-trade

🔴 AUTO OFF Nonaktifkan auto-trade

📜 HISTORY Riwayat trade dan performa

🔄 REFRESH Update data terbaru

❓ HELP Panduan lengkap

---

⏰ NOTIFIKASI TELEGRAM (Otomatis)

Event Waktu Isi Notifikasi
Hourly Update Setiap jam (01:00, 02:00, dst) Balance, price, technical signal, sentiment, posisi
Auto Trade Saat eksekusi BUY/SELL Action, price, SL, TP, reason
Stop Loss Hit Saat harga kena SL Entry, exit, PnL
Take Profit Hit Saat harga kena TP Entry, exit, PnL
Reverse Trading Saat sinyal berlawanan Close old position, open new position

---

🛡️ MANAJEMEN RISIKO

Parameter Nilai Keterangan
Dynamic Stop Loss 1.5x - 2x ATR (min 0.8%, max 3%) Berdasarkan volatilitas pasar
Take Profit 3% dari entry Fixed
Leverage 25x KuCoin Futures
Monitoring SL/TP Setiap 10 detik Real-time
Auto-trade interval 1 jam Analisis setiap jam
Minimum balance $2.66 1 contract BTC

---

📊 RINGKASAN FITUR

Fitur Status Keterangan
6 AI Agent ✅ AKTIF Technical, Sentiment, News, Exchange, Whale, Risk

AI Primary (Qwen) ✅ AKTIF OpenRouter (gratis)

AI Fallback (Groq) ✅ AKTIF Llama 3.1 8B

Auto-trade ✅ AKTIF Setiap 1 jam

Reverse Trading ✅ AKTIF Tutup posisi jika sinyal berlawanan

Dynamic Stop Loss ✅ AKTIF Berdasarkan ATR (volatilitas)

Monitoring SL/TP ✅ AKTIF Setiap 10 detik

Hourly Notification ✅ AKTIF Setiap jam ke Telegram

Database History ✅ AKTIF SQLite untuk riwayat trade

Auto ON/OFF ✅ AKTIF Via tombol Telegram

Multi-timeframe ✅ AKTIF 15m, 1h, 4h, 1d

Funding Rate ✅ AKTIF 8 exchange

Order Book Depth ✅ AKTIF Binance order book

On-Chain Data ✅ AKTIF Whale netflow, MPI, premium

---

📄 LISENSI

MIT License - Copyright (c) 2026 sasolbezzet

---

🤝 KONTAK

· Telegram: @Davabezzet
· GitHub: sasolbezzet

---

⭐ Jangan lupa beri star jika proyek ini bermanfaat!

```
