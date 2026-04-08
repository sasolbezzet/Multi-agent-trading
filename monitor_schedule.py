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
    from telegram import Bot
    
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
    from db_helper import get_signal_stats
    total_signals, today_signals, buys, sells = get_signal_stats()
    
    # 3. Cek balance
    try:
        from utils.kucoin_api import KuCoinFutures
        kucoin = KuCoinFutures(
            api_key=os.getenv('KUCOIN_API_KEY'),
            api_secret=os.getenv('KUCOIN_API_SECRET'),
            api_passphrase=os.getenv('KUCOIN_API_PASSPHRASE')
        )
        balance = kucoin.get_balance()
        position = kucoin.get_position()
    except:
        balance = 0
        position = {"has_position": False}
    
    # 4. Cek performa 24 jam dari sinyal
    try:
        from backtest_engine import BacktestEngine
        engine = BacktestEngine(initial_balance=1000, leverage=25)
        results = engine.run(days=1)
        daily_return = results['total_return'] if results else 0
        win_rate = results['win_rate'] if results else 0
    except:
        daily_return = 0
        win_rate = 0
    
    # Buat pesan
    msg = "📊 *BOT MONITORING REPORT*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"🕐 *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
    msg += f"🤖 *Bot Status:* {bot_status}\n"
    msg += f"💰 *Balance:* ${balance:.2f}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 *Total Signals:* {total_signals}\n"
    msg += f"📈 *Today Signals:* {today_signals}\n"
    msg += f"🟢 *BUY Signals:* {buys}\n"
    msg += f"🔴 *SELL Signals:* {sells}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📈 *24h Return:* {daily_return:+.2f}%\n"
    msg += f"📊 *Win Rate:* {win_rate}%\n"
    
    if position['has_position']:
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📌 *Active Position:* {position['side'].upper()}\n"
        msg += f"   Entry: ${position['entry']:.2f}\n"
        msg += f"   PnL: {position['pnl']:+.2f} USDT\n"
    
    msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🕐 Next report: {(datetime.now() + timedelta(hours=6)).strftime('%H:%M')} UTC"
    
    await bot.send_message(chat_id, msg, parse_mode='Markdown')
    print(f"Monitoring report sent at {datetime.now()}")

async def scheduler():
    """Jalankan monitoring tepat pada 00:00, 06:00, 12:00, 18:00 UTC"""
    print("Monitoring scheduler started")
    print("Will send reports at 00:00, 06:00, 12:00, 18:00 UTC")
    
    while True:
        now = datetime.now()
        
        # Jadwal: 00:00, 06:00, 12:00, 18:00
        scheduled_times = [0, 6, 12, 18]
        
        # Cari waktu berikutnya
        next_hour = None
        for hour in scheduled_times:
            if hour > now.hour:
                next_hour = hour
                break
        
        if next_hour is None:
            next_hour = scheduled_times[0]
            next_run = now.replace(hour=next_hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:
            next_run = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
        
        wait_seconds = (next_run - now).total_seconds()
        
        print(f"Next report at {next_run.strftime('%Y-%m-%d %H:%M:%S')} UTC (in {wait_seconds/3600:.1f} hours)")
        await asyncio.sleep(wait_seconds)
        
        # Kirim laporan
        await send_monitoring_report()

if __name__ == "__main__":
    asyncio.run(scheduler())
