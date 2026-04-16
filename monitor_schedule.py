#!/usr/bin/env python3
"""
Monitoring otomatis setiap 6 jam (00:00, 06:00, 12:00, 18:00 UTC)
"""
import asyncio
import os
import sys
import subprocess
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

async def send_monitoring_report():
    """Kirim laporan monitoring ke Telegram"""
    try:
        from telegram import Bot
    except ImportError:
        print("Telegram module not installed")
        return
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("Telegram credentials not found")
        return
    
    bot = Bot(token=token)
    
    # 1. Cek status bot
    result = subprocess.run(["sudo", "supervisorctl", "status", "groq-bot"], capture_output=True, text=True)
    bot_status = "✅ RUNNING" if "RUNNING" in result.stdout else "❌ STOPPED"
    
    # 2. Cek jumlah sinyal
    try:
        import sqlite3
        conn = sqlite3.connect('/home/ubuntu/groq_trading_bot/signals.db')
        cursor = conn.cursor()
        
        # Total sinyal
        cursor.execute("SELECT COUNT(*) FROM signals_history")
        total_signals = cursor.fetchone()[0]
        
        # Sinyal hari ini
        cursor.execute("SELECT COUNT(*) FROM signals_history WHERE date(timestamp) = date('now')")
        today_signals = cursor.fetchone()[0]
        
        # BUY/SELL hari ini
        cursor.execute("SELECT ai_action, COUNT(*) FROM signals_history WHERE date(timestamp) = date('now') GROUP BY ai_action")
        actions = cursor.fetchall()
        buys = 0
        sells = 0
        for action, count in actions:
            if action == 'BUY':
                buys = count
            elif action == 'SELL':
                sells = count
        
        conn.close()
    except Exception as e:
        total_signals = 0
        today_signals = 0
        buys = 0
        sells = 0
        print(f"DB error: {e}")
    
    # 3. Cek balance
    try:
        sys.path.insert(0, '/home/ubuntu/groq_trading_bot')
        from utils.kucoin_api import KuCoinFutures
        
        kucoin = KuCoinFutures(
            api_key=os.getenv('KUCOIN_API_KEY'),
            api_secret=os.getenv('KUCOIN_API_SECRET'),
            api_passphrase=os.getenv('KUCOIN_API_PASSPHRASE')
        )
        balance = kucoin.get_balance()
        position = kucoin.get_position()
    except Exception as e:
        balance = 0
        position = {'has_position': False}
        print(f"KuCoin error: {e}")
    
    # 4. Buat pesan
    msg = f"📊 *6-HOUR MONITORING REPORT*\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🤖 Bot Status: {bot_status}\n"
    msg += f"💰 Balance: ${balance:.2f}\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 SIGNAL STATISTICS\n"
    msg += f"   Total Signals: {total_signals}\n"
    msg += f"   Today: {today_signals}\n"
    msg += f"   BUY: {buys} | SELL: {sells}\n"
    
    if position['has_position']:
        pnl_emoji = "🟢" if position['pnl'] >= 0 else "🔴"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📌 ACTIVE POSITION\n"
        msg += f"   Side: {position['side'].upper()}\n"
        msg += f"   Entry: ${position['entry']:.2f}\n"
        msg += f"   PnL: {pnl_emoji} {position['pnl']:+.2f} USDT\n"
    
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"⏰ Next report in 6 hours"
    
    # Kirim pesan
    await bot.send_message(chat_id, msg, parse_mode='Markdown')
    print(f"✅ Monitoring report sent at {datetime.now()}")

async def main():
    print("🕐 6-HOUR MONITORING STARTED")
    print("   Schedule: 00:00, 06:00, 12:00, 18:00 UTC")
    
    while True:
        now = datetime.now()
        # Hitung jam berikutnya yang merupakan kelipatan 6
        current_hour = now.hour
        next_hour = ((current_hour // 6) + 1) * 6
        if next_hour >= 24:
            next_hour = 0
            next_run = now.replace(hour=next_hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:
            next_run = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
        
        if next_run <= now:
            next_run += timedelta(hours=6)
        
        wait_seconds = (next_run - now).total_seconds()
        print(f"📅 Next report at {next_run.strftime('%Y-%m-%d %H:%M:%S')} (in {wait_seconds/3600:.1f} hours)")
        await asyncio.sleep(wait_seconds)
        await send_monitoring_report()

if __name__ == "__main__":
    asyncio.run(main())
