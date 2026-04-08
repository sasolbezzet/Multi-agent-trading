#!/usr/bin/env python3
"""
Notifikasi per jam yang dikirim 5 menit setelah jam (agar AI analysis selesai)
Menampilkan: Balance, Price, Position, PnL, SL/TP, dan Prediksi AI terakhir
"""

import asyncio
import os
import sys
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, '/home/ubuntu/groq_trading_bot')
from utils.kucoin_api import KuCoinFutures
from dotenv import load_dotenv
from telegram import Bot

load_dotenv('/home/ubuntu/groq_trading_bot/.env')

async def get_ai_prediction():
    """Ambil prediksi AI terbaru dari database signals"""
    try:
        conn = sqlite3.connect('/home/ubuntu/groq_trading_bot/signals.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ai_action, ai_confidence, ai_reason 
            FROM signals_history 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()
        if result:
            return {
                "action": result[0], 
                "confidence": result[1], 
                "reason": result[2][:100] if result[2] else ""
            }
    except Exception as e:
        print(f"Error getting AI prediction: {e}")
    return {"action": "HOLD", "confidence": 50, "reason": "No data available"}

async def send_hourly_update():
    """Kirim update setiap jam, 5 menit setelah jam (14:05, 15:05, dst)"""
    kucoin = KuCoinFutures(
        api_key=os.getenv('KUCOIN_API_KEY'),
        api_secret=os.getenv('KUCOIN_API_SECRET'),
        api_passphrase=os.getenv('KUCOIN_API_PASSPHRASE')
    )
    
    print("🕐 Notifikasi per jam akan dikirim setiap jam +5 menit")
    print("   Contoh: 14:05, 15:05, 16:05, dst")
    
    while True:
        now = datetime.now()
        
        # Hitung waktu berikutnya: jam berikutnya + 5 menit
        next_run = now.replace(minute=5, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(hours=1)
        
        wait_seconds = (next_run - now).total_seconds()
        print(f"📅 Next notification at {next_run.strftime('%Y-%m-%d %H:%M:%S')} UTC (in {wait_seconds/60:.1f} minutes)")
        
        await asyncio.sleep(wait_seconds)
        
        try:
            price = kucoin.get_price()
            balance = kucoin.get_balance()
            position = kucoin.get_position()
            ai = await get_ai_prediction()
            
            # Hitung SL/TP
            sl_info = ""
            tp_info = ""
            if position['has_position']:
                entry = position['entry']
                side = position['side']
                if side == 'long':
                    sl = entry * 0.985
                    tp = entry * 1.03
                    sl_pct = "-1.5%"
                    tp_pct = "+3%"
                else:
                    sl = entry * 1.015
                    tp = entry * 0.97
                    sl_pct = "+1.5%"
                    tp_pct = "-3%"
                sl_info = f"   🛡️ SL: ${sl:.2f} ({sl_pct})"
                tp_info = f"   🎯 TP: ${tp:.2f} ({tp_pct})"
            
            # Emoji untuk sinyal
            signal_emoji = "🟢" if ai['action'] == 'BUY' else "🔴" if ai['action'] == 'SELL' else "⚪"
            pnl_emoji = "🟢" if position.get('pnl', 0) >= 0 else "🔴"
            
            # Buat pesan dengan format rapi
            msg = f"⏰ *HOURLY UPDATE*\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"🕐 {datetime.now().strftime('%H:%M:%S')} UTC\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"💰 Balance: ${balance:.2f}\n"
            msg += f"📈 BTC: ${price:,.0f}\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            if position['has_position']:
                msg += f"📌 *ACTIVE POSITION*\n"
                msg += f"   Side: {position['side'].upper()}\n"
                msg += f"   Entry: ${position['entry']:.2f}\n"
                msg += f"   Current: ${position['current']:.2f}\n"
                msg += f"   PnL: {pnl_emoji} {position['pnl']:+.2f} USDT\n"
                msg += f"{sl_info}\n"
                msg += f"{tp_info}\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            else:
                msg += f"📌 Position: NONE\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            msg += f"🤖 *AI PREDICTION* (from last hourly signal)\n"
            msg += f"   {signal_emoji} Signal: {ai['action']}\n"
            msg += f"   📊 Confidence: {ai['confidence']}%\n"
            if ai['reason']:
                reason_short = ai['reason'][:80] + "..." if len(ai['reason']) > 80 else ai['reason']
                msg += f"   📝 Reason: {reason_short}\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"⏰ Next: {(datetime.now() + timedelta(hours=1)).strftime('%H:%M')} UTC (jam +5 menit)"
            
            # Kirim ke Telegram
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            if token and chat_id:
                bot = Bot(token=token)
                await bot.send_message(chat_id, msg, parse_mode='Markdown')
                print(f"✅ Notification sent at {datetime.now().strftime('%H:%M:%S')}")
            else:
                print("⚠️ Telegram credentials not found")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(send_hourly_update())
