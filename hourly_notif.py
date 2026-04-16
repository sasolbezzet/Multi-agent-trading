#!/usr/bin/env python3
"""
Notifikasi per 30 menit (00:05, 00:35, 01:05, 01:35, dst)
"""
import asyncio
import requests
import os
import sys
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.insert(0, '/home/ubuntu/groq_trading_bot')
from utils.kucoin_api import KuCoinFutures

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_message(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        r = requests.post(url, json={'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}, timeout=10)
        return r.ok
    except Exception as e:
        print(f"Error: {e}")
        return False


def get_risk_reason():
    """Ambil alasan mengapa risk agent block trading"""
    try:
        conn = sqlite3.connect('/home/ubuntu/groq_trading_bot/signals.db')
        c = conn.cursor()
        # Cek apakah kolom risk_reason ada
        c.execute("PRAGMA table_info(signals_history)")
        columns = [col[1] for col in c.fetchall()]
        if 'risk_reason' in columns:
            c.execute("SELECT risk_reason FROM signals_history WHERE risk_reason IS NOT NULL AND risk_reason != '' ORDER BY timestamp DESC LIMIT 1")
            r = c.fetchone()
            if r and r[0]:
                return r[0]
        # Fallback: ambil dari reason di risk_res
        c.execute("SELECT reason FROM signals_history WHERE reason IS NOT NULL ORDER BY timestamp DESC LIMIT 1")
        r = c.fetchone()
        if r and r[0]:
            return r[0]
        conn.close()
    except Exception as e:
        print(f"Error get_risk_reason: {e}")
    return "Unknown reason"

def get_ai_prediction():
    try:
        conn = sqlite3.connect('/home/ubuntu/groq_trading_bot/signals.db')
        c = conn.cursor()
        c.execute("SELECT ai_action, ai_confidence, ai_reason FROM signals_history ORDER BY timestamp DESC LIMIT 1")
        r = c.fetchone()
        conn.close()
        if r:
            return {"action": r[0], "confidence": r[1], "reason": r[2][:100] if r[2] else ""}
    except:
        pass
    return {"action": "HOLD", "confidence": 50, "reason": "No data"}

async def send_notification():
    try:
        kucoin = KuCoinFutures(
            api_key=os.getenv('KUCOIN_API_KEY'),
            api_secret=os.getenv('KUCOIN_API_SECRET'),
            api_passphrase=os.getenv('KUCOIN_API_PASSPHRASE')
        )
        
        price = kucoin.get_price()
        balance = kucoin.get_balance()
        position = kucoin.get_position()
        ai = get_ai_prediction()
        
        signal_emoji = "🟢" if ai['action'] == 'BUY' else "🔴" if ai['action'] == 'SELL' else "⚪"
        pnl_emoji = "🟢" if position.get('pnl', 0) >= 0 else "🔴"
        
        msg = f"⏰ *30-MINUTE UPDATE*\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🕐 {datetime.now().strftime('%H:%M:%S')} UTC\n"
        msg += f"💰 Balance: ${balance:.2f}\n"
        msg += f"📈 BTC: ${price:,.0f}\n"
        
        if position['has_position']:
            msg += f"📌 Position: {position['side'].upper()} @ ${position['entry']:.2f}\n"
            msg += f"   PnL: {pnl_emoji} {position['pnl']:+.2f} USDT\n"
        else:
            msg += f"📌 Position: NONE\n"
        
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🤖 AI: {signal_emoji} {ai['action']} ({ai['confidence']}%)\n"
        
        # Ambil risk reason dari database jika AI decision HOLD atau risk block
        if ai['action'] == 'HOLD':
            try:
                conn = sqlite3.connect('/home/ubuntu/groq_trading_bot/signals.db')
                c = conn.cursor()
                c.execute("SELECT risk_reason FROM signals_history WHERE risk_reason IS NOT NULL AND risk_reason != '' ORDER BY timestamp DESC LIMIT 1")
                r = c.fetchone()
                if r and r[0]:
                    msg += f"📝 Risk agent blocks trading: {r[0][:80]}"
                else:
                    msg += f"📝 {ai['reason'][:80] if ai['reason'] else 'No signal'}"
                conn.close()
            except:
                msg += f"📝 {ai['reason'][:80] if ai['reason'] else 'No signal'}"
        else:
            if ai['reason']:
                msg += f"📝 {ai['reason'][:80]}"
        
        send_message(msg)
        print(f"✅ Notification sent at {datetime.now()}")
        
    except Exception as e:
        print(f"Error: {e}")

async def main():
    print("🕐 30-minute notification sender started")
    print("   Schedule: 00:05, 00:35, 01:05, 01:35...")
    
    while True:
        now = datetime.now()
        minute = now.minute
        
        # Hitung target menit berikutnya
        if minute < 5:
            target_minute = 5
            next_run = now.replace(minute=target_minute, second=0, microsecond=0)
        elif minute < 35:
            target_minute = 35
            next_run = now.replace(minute=target_minute, second=0, microsecond=0)
        else:
            target_minute = 5
            # Pergantian hari jika jam 23:35+
            if now.hour >= 23:
                next_run = now.replace(hour=0, minute=target_minute, second=0, microsecond=0) + timedelta(days=1)
            else:
                next_run = now.replace(hour=now.hour + 1, minute=target_minute, second=0, microsecond=0)
        
        if next_run <= now:
            next_run += timedelta(minutes=30)
        
        wait_seconds = (next_run - now).total_seconds()
        print(f"📅 Next: {next_run.strftime('%Y-%m-%d %H:%M:%S')} (in {wait_seconds/60:.1f} min)")
        await asyncio.sleep(wait_seconds)
        await send_notification()

if __name__ == "__main__":
    asyncio.run(main())
