from websocket_kucoin import get_realtime_price
import os
import asyncio

# Global variable untuk trailing stop
current_trailing_sl = None

import json
import os

AUTO_TRADE_FILE = "/home/ubuntu/groq_trading_bot/.auto_trade_status.json"

def load_auto_status():
    try:
        with open(AUTO_TRADE_FILE, 'r') as f:
            return json.load(f).get('enabled', True)
    except:
        return True

def save_auto_status(status):
    try:
        with open(AUTO_TRADE_FILE, 'w') as f:
            json.dump({'enabled': status}, f)
    except:
        pass

# Load status from file
AUTO_TRADE_ENABLED = load_auto_status()
print(f"🔧 Auto trade status loaded: {AUTO_TRADE_ENABLED}")

import logging
import requests
import time
import base64
import hashlib
import hmac
import json
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Import agents
from agents.technical_agent import TechnicalAgent
from agents.sentiment_agent import SentimentAgent
from agents.news_social_agent import NewsSocialAgent
from agents.exchange_agent import ExchangeAgent
from agents.whale_agent import WhaleAgent
from agents.risk_agent import RiskAgent
from agents.groq_orchestrator import GroqOrchestrator
from utils.kucoin_api import KuCoinFutures
# ============================================================
# AUTO-TRADE TOGGLE (ON/OFF)
# ============================================================

def set_auto_trade(status):
    global AUTO_TRADE_ENABLED
    AUTO_TRADE_ENABLED = status
    save_auto_status(status)
    logger.info(f"Auto-trade set to: {status}")

def get_auto_trade():
    return AUTO_TRADE_ENABLED


load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Initialize agents
technical = TechnicalAgent()
sentiment = SentimentAgent()
news_social = NewsSocialAgent()
exchange = ExchangeAgent()
whale = WhaleAgent()
risk = RiskAgent()
groq = GroqOrchestrator()
kucoin = KuCoinFutures(
    api_key=os.getenv('KUCOIN_API_KEY'),
    api_secret=os.getenv('KUCOIN_API_SECRET'),
    api_passphrase=os.getenv('KUCOIN_API_PASSPHRASE')
)

async def get_analysis():
    price = await get_realtime_price()
    balance = kucoin.get_balance()
    position = kucoin.get_position()
    has_position = position['has_position']
    tech = await technical.analyze()
    sent = await sentiment.analyze()
    news_social_data = await news_social.analyze()
    news = news_social_data
    exch = await exchange.analyze()
    whale_data = await whale.analyze()
    risk_res = await risk.analyze(balance, has_position, position if has_position else None, tech.get("atr_percent"), tech.get("volume_ratio"))
    dec = await groq.decide(
        technical=tech, sentiment=sent, news_social=news,
        exchange=exch, whale=whale_data, risk=risk_res, current_price=price,
        has_position=has_position, last_action=None
    )
    
    # Simpan sinyal ke database
    from db_helper import save_signal_to_db
    save_signal_to_db(price, tech, sent, news, exch, whale_data, risk_res, dec)
    
    return tech, sent, news, exch, whale_data, risk_res, dec, price, balance, has_position, position

def get_emoji(signal):
    if signal == 'BUY':
        return '🟢'
    elif signal == 'SELL':
        return '🔴'
    else:
        return '⚪'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 MARKET STATUS", callback_data="status")],
        [InlineKeyboardButton("🔍 FORCE SIGNAL", callback_data="force_signal")],
        [InlineKeyboardButton("💰 BALANCE", callback_data="balance")],
        [InlineKeyboardButton("📈 POSITION", callback_data="position")],
        [InlineKeyboardButton("🔴 CLOSE POSITION", callback_data="close")],
        [InlineKeyboardButton("🔄 REFRESH", callback_data="refresh")],
        [InlineKeyboardButton("❓ HELP", callback_data="help")],
        [InlineKeyboardButton("🟢 AUTO ON", callback_data="auto_on"), InlineKeyboardButton("🔴 AUTO OFF", callback_data="auto_off")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_msg = (
        "🤖 *GROQ MULTI-AGENT TRADING BOT*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 *6 AI Agents Working Together:*\n"
        "┌─────────────────────────────────┐\n"
        "│ 📊 Technical Analyst (RSI/MACD) │\n"
        "│ 📰 Sentiment Analyst (F&G)      │\n"
        "│ 📱 News & Social Analyst       │\n"
        "│ 💱 Exchange Flow Analyst       │\n"
        "│ 🐋 Whale Tracker (Arkham)      │\n"
        "│ 🛡️ Risk Manager (SL/TP)        │\n"
        "└─────────────────────────────────┘\n\n"
        "🧠 *AI Orchestrator* (Qwen 3.6 Plus / Groq)\n"
        "   → Menggabungkan semua analisis\n\n"
        "⚡ *Auto-Trading Active*\n"
        "   → Analisis setiap 30 menit\n"
        "   → Eksekusi otomatis ke KuCoin\n\n"
        "📌 *Tekan tombol di bawah untuk mulai*"
    )
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id

    if data == "status":
        try:
            tech, sent, news_social_data, exch, whale_data, risk_res, dec, price, balance, has_pos, pos = await get_analysis()
            news = news_social_data
            msg = (
                "📊 *MARKET STATUS*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 Balance: ${balance:.2f}\n"
                f"📈 BTC Price: ${price:,.2f}\n\n"
                "🤖 *AGENT SIGNALS*\n"
                f"┌─────────────────────────────────┐\n"
                f"│ 📊 Technical : {get_emoji(tech['signal'])} {tech['signal']} ({tech['confidence']}%)\n"
                f"│ 📰 Sentiment : {get_emoji(sent['signal'])} {sent['signal']} ({sent['confidence']}%)\n"
                f"│ 📱 News      : {get_emoji(news['signal'])} {news['signal']} ({news['confidence']}%)\n"
                f"│ 💱 Exchange  : {get_emoji(exch['signal'])} {exch['signal']} ({exch['confidence']}%)\n"
                f"│ 🐋 Whale     : {get_emoji(whale_data['signal'])} {whale_data['signal']} ({whale_data['confidence']}%)\n"
                f"└─────────────────────────────────┘\n\n"
                f"🛡️ Risk: {'✅ CAN TRADE' if risk_res.get('can_trade') else '❌ CANNOT TRADE'}\n"
            )
            if has_pos:
                msg += (
                    f"\n📌 *ACTIVE POSITION*\n"
                    f"   Side: {'🟢 LONG' if pos['side'] == 'long' else '🔴 SHORT'}\n"
                    f"   Entry: ${pos['entry']:.2f}\n"
                    f"   Current: ${pos['current']:.2f}\n"
                    f"   P&L: {pos['pnl']:+.2f} USDT\n"
                )
            await context.bot.send_message(chat_id, msg, parse_mode='Markdown')
        except Exception as e:
            await context.bot.send_message(chat_id, f"❌ Error: {str(e)[:200]}", parse_mode='Markdown')


    elif data == "status":
        try:
            tech, sent, news_social_data, exch, whale_data, risk_res, dec, price, balance, has_pos, pos = await get_analysis()
            news = news_social_data
            msg = (
                "📊 *MARKET STATUS*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 Balance: ${balance:.2f}\n"
                f"📈 BTC Price: ${price:,.2f}\n\n"
                "🤖 *AGENT SIGNALS*\n"
                f"┌─────────────────────────────────┐\n"
                f"│ 📊 Technical : {get_emoji(tech['signal'])} {tech['signal']} ({tech['confidence']}%)\n"
                f"│ 📰 Sentiment : {get_emoji(sent['signal'])} {sent['signal']} ({sent['confidence']}%)\n"
                f"│ 📱 News      : {get_emoji(news['signal'])} {news['signal']} ({news['confidence']}%)\n"
                f"│ 💱 Exchange  : {get_emoji(exch['signal'])} {exch['signal']} ({exch['confidence']}%)\n"
                f"│ 🐋 Whale     : {get_emoji(whale_data['signal'])} {whale_data['signal']} ({whale_data['confidence']}%)\n"
                f"└─────────────────────────────────┘\n\n"
                f"🛡️ Risk: {'✅ CAN TRADE' if risk_res.get('can_trade') else '❌ CANNOT TRADE'}\n"
            )
            if has_pos:
                msg += (
                    f"\n📌 *ACTIVE POSITION*\n"
                    f"   Side: {'🟢 LONG' if pos['side'] == 'long' else '🔴 SHORT'}\n"
                    f"   Entry: ${pos['entry']:.2f}\n"
                    f"   Current: ${pos['current']:.2f}\n"
                    f"   P&L: {pos['pnl']:+.2f} USDT\n"
                )
            await context.bot.send_message(chat_id, msg, parse_mode='Markdown')
        except Exception as e:
            await context.bot.send_message(chat_id, f"❌ Error: {str(e)[:200]}", parse_mode='Markdown')

    elif data == "force_signal":
        await context.bot.send_message(chat_id, "🔍 *Analyzing with 6 Agents...*", parse_mode='Markdown')
        try:
            tech, sent, news_social_data, exch, whale_data, risk_res, dec, price, balance, has_pos, pos = await get_analysis()
            news = news_social_data
            action = dec.get('action', 'HOLD')
            confidence = dec.get('confidence', 50)
            reason = dec.get('reason', '')
            msg = (
                "🎯 *FINAL TRADING SIGNAL*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📊 *Individual Agent Analysis:*\n"
                "┌─────────────────────────────────────────┐\n"
                f"│ 📊 Technical  : {tech['signal']} ({tech['confidence']}%)\n"
                f"│    └─ RSI: {tech.get('rsi', 'N/A')} | Trend: {tech.get('trend', 'N/A')}\n"
                f"│ 📰 Sentiment : {sent['signal']} ({sent['confidence']}%)\n"
                f"│    └─ Fear & Greed: {sent.get('fear_greed', 'N/A')}\n"
                f"│ 📱 News      : {news['signal']} ({news['confidence']}%)\n"
                f"│ 💱 Exchange  : {exch['signal']} ({exch['confidence']}%)\n"
                f"│    └─ {exch.get('reason', '')}\n"
                f"│ 🐋 Whale     : {whale_data['signal']} ({whale_data['confidence']}%)\n"
                f"│    └─ {whale_data.get('reason', '')[:50]}\n"
                "└─────────────────────────────────────────┘\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🧠 *AI FINAL DECISION*\n"
                f"   ➜ *{action}* ({confidence}% confidence)\n"
                f"   📝 Reason: {reason}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 Current Price: ${price:,.2f}\n"
            )
            if has_pos:
                msg += (
                    f"\n⚠️ *EXISTING POSITION*\n"
                    f"   Side: {pos['side'].upper()}\n"
                    f"   Entry: ${pos['entry']:.2f}\n"
                    f"   P&L: {pos['pnl']:+.2f} USDT\n"
                )
            if risk_res.get("can_trade"):
                msg += "\n[RISK] Status: ✅ CAN TRADE"
            else:
                risk_reason = risk_res.get("reason", "Unknown")
                msg += "\n[RISK] Status: ❌ CANNOT TRADE"
                msg += f"\n    Reason: {risk_reason}"
            await context.bot.send_message(chat_id, msg, parse_mode='Markdown')
        except Exception as e:
            await context.bot.send_message(chat_id, f"❌ Error: {str(e)[:200]}", parse_mode='Markdown')

    elif data == "balance":
        balance = kucoin.get_balance()
        msg = f"💰 *Balance:* ${balance:.2f} USDT"
        await context.bot.send_message(chat_id, msg, parse_mode='Markdown')

    elif data == "position":
        pos = kucoin.get_position()
        if pos['has_position']:
            entry = pos['entry']
            side = pos['side']
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
            side_text = "LONG" if side == "long" else "SHORT"
            side_icon = "🟢" if side == "long" else "🔴"
            msg = f"📈 *POSITION DETAILS*\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"Side: {side_icon} {side_text}\n"
            msg += f"Entry: ${entry:.2f}\n"
            msg += f"Current: ${pos['current']:.2f}\n"
            msg += f"PnL: {pos['pnl']:+.2f} USDT\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"🎯 *RISK MANAGEMENT*\n"
            msg += f"🛡️ Stop Loss: ${sl:.2f} ({sl_pct})\n"
            msg += f"🎯 Take Profit: ${tp:.2f} ({tp_pct})"
        else:
            msg = "📌 *NO ACTIVE POSITION*\n\nUse FORCE SIGNAL to get trading signals"
        await context.bot.send_message(chat_id, msg, parse_mode='Markdown')


    elif data == "confirm_close":
        pos = kucoin.get_position()
        if pos['has_position']:
            result = kucoin.close_position()
            if result:
                msg = "🔴 *POSITION CLOSED*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                msg += "Side: " + ("🟢 LONG" if pos['side'] == "long" else "🔴 SHORT") + "\n"
                msg += "Entry: $" + format(pos['entry'], '.2f') + "\n"
                msg += "Close: $" + format(pos['current'], '.2f') + "\n"
                msg += "PnL: " + format(pos['pnl'], '+.2f') + " USDT"
            else:
                msg = "❌ *CLOSE FAILED*\nGagal menutup posisi. Coba lagi."
        else:
            msg = "📌 *POSITION ALREADY CLOSED*\nPosisi sudah tidak ada."
        await context.bot.send_message(chat_id, msg, parse_mode='Markdown')
    
    elif data == "cancel_close":
        msg = "❌ *CLOSE CANCELLED*\nPosisi tetap terbuka."
        await context.bot.send_message(chat_id, msg, parse_mode='Markdown')

    elif data == "close":
        pos = kucoin.get_position()
        if pos["has_position"]:
            confirm_keyboard = [
                [InlineKeyboardButton("✅ YES, CLOSE", callback_data="confirm_close")],
                [InlineKeyboardButton("❌ CANCEL", callback_data="cancel_close")]
            ]
            confirm_markup = InlineKeyboardMarkup(confirm_keyboard)
            msg = "⚠️ *KONFIRMASI CLOSE POSITION*\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "Side: " + ("🟢 LONG" if pos["side"] == "long" else "🔴 SHORT") + "\n"
            msg += "Entry: $" + format(pos["entry"], ".2f") + "\n"
            msg += "Current: $" + format(pos["current"], ".2f") + "\n"
            msg += "PnL: " + format(pos["pnl"], "+.2f") + " USDT\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "Yakin ingin menutup posisi?"
            await context.bot.send_message(chat_id, msg, reply_markup=confirm_markup, parse_mode="Markdown")
        else:
            msg = "📌 *NO ACTIVE POSITION*\n\nTidak ada posisi untuk ditutup"
            try:
                await asyncio.wait_for(context.bot.send_message(chat_id, msg, parse_mode="Markdown"), timeout=30)
            except asyncio.TimeoutError:
                print(f"Telegram timeout for chat {chat_id}")
    elif data == "refresh":
        try:
            balance = kucoin.get_balance()
            price = await get_realtime_price()
            pos = kucoin.get_position()
            has_pos = pos['has_position']
            msg = f"✅ *DATA REFRESHED*\n💰 Balance: ${balance:.2f}\n📈 BTC: ${price:,.2f}\n"
            if has_pos:
                msg += f"📌 Position: {pos['side'].upper()} @ ${pos['entry']:.2f} | PnL: {pos['pnl']:+.2f}"
            else:
                msg += "📌 No active position"
            await context.bot.send_message(chat_id, msg, parse_mode='Markdown')
        except Exception as e:
            await context.bot.send_message(chat_id, f"Error: {str(e)}")

    elif data == "auto_on":
        logger.info(f"📱 AUTO ON button pressed by user {update.effective_user.id}")
        set_auto_trade(True)
        await context.bot.send_message(chat_id, "✅ Auto-Trade ENABLED", parse_mode="Markdown")
    
    elif data == "auto_off":
        logger.info(f"📱 AUTO OFF button pressed by user {update.effective_user.id}")
        set_auto_trade(False)
        await context.bot.send_message(chat_id, "❌ Auto-Trade DISABLED", parse_mode="Markdown")
    
    elif data == "help":
        msg = (
            "❓ *Help*\n"
            "• STATUS - Show market status and agent signals\n"
            "• FORCE SIGNAL - Run full analysis with 6 agents\n"
            "• BALANCE - Check KuCoin balance\n"
            "• POSITION - Current position details\n"
            "• CLOSE - Close active position\n"
            "• REFRESH - Refresh data"
        )
        await context.bot.send_message(chat_id, msg, parse_mode='Markdown')

class TradingBot:
    async def calculate_position_size(self, balance, price, leverage=25):
        """Hitung posisi size berdasarkan 50% dari balance"""
        risk_capital = balance * 0.5
        contract_value = price * 0.001
        margin_per_contract = contract_value / leverage
        size = int(risk_capital / margin_per_contract)
        
        if size < 1:
            logger.warning(f"Insufficient balance for 1 contract with 50% rule. Balance: ${balance:.2f}, Need: ${margin_per_contract:.2f}")
            return 0
        
        size = min(size, 5)
        logger.info(f"Position size: {size} contract(s) (50% of ${balance:.2f})")
        return size
    def __init__(self):
        self.symbol = "XBTUSDTM"
        self.analysis_interval = 30
        self.scheduler = AsyncIOScheduler()
        
        # Reverse trade cooldown
        self.reverse_cooldown_minutes = 60
        self.last_reverse_time = {}
        self.application = None
        self.kucoin = kucoin

    
    def check_reverse_cooldown(self, symbol):
        """Cek apakah masih dalam cooldown reverse trade"""
        import time
        last_reverse = self.last_reverse_time.get(symbol, 0)
        cooldown_seconds = self.reverse_cooldown_minutes * 60
        if time.time() - last_reverse < cooldown_seconds:
            remaining = int((cooldown_seconds - (time.time() - last_reverse)) / 60)
            logger.info(f"⏰ Reverse cooldown active for {symbol}, remaining {remaining} minutes")
            return True
        return False
    
    def record_reverse_trade(self, symbol):
        """Catat waktu reverse trade"""
        import time
        self.last_reverse_time[symbol] = time.time()
        logger.info(f"📝 Recorded reverse trade for {symbol}, cooldown {self.reverse_cooldown_minutes} minutes")

    async def analyze_and_trade(self):
        print("🔍 ANALYZE_AND_TRADE CALLED")
        logger.info("🔍 ANALYZE_AND_TRADE CALLED")
        import sys
        sys.stdout.flush()
        if not get_auto_trade():
            logger.info("🔴 AUTO TRADE IS DISABLED - Skipping all trades")
            return
        # CEK AUTO TRADE STATUS
            logger.info("🔴 AUTO TRADE IS DISABLED - Skipping execution")
            return
        # Cek apakah auto trade diaktifkan
            return
        # Cek apakah auto trade diaktifkan
            return
        logger.info("Running scheduled analysis...")
        try:
            tech, sent, news_social_data, exch, whale_data, risk_res, dec, price, balance, has_pos, pos = await get_analysis()
            news = news_social_data
            action = dec.get('action', 'HOLD')
            
            # ========== REVERSE TRADING ==========
            # Jika ada posisi dan sinyal berlawanan, tutup posisi dulu
            if has_pos and action in ['BUY', 'SELL']:
                current_side = pos['side']
                if (action == 'BUY' and current_side == 'short') or (action == 'SELL' and current_side == 'long'):
                    logger.info(f"Signal {action} opposite to current {current_side}. Closing position...")
                    close_result = kucoin.close_position()
                    if close_result:
                        await self.send_telegram_message(f"🔴 Closed {current_side.upper()} due to new {action} signal. PnL: {pos['pnl']:+.2f} USDT")
                        has_pos = False
                        await asyncio.sleep(2)
                        # Buka posisi baru sesuai sinyal
                                                # Cek cooldown sebelum reverse
                        if self.check_reverse_cooldown(symbol):
                            logger.info(f"⏰ Reverse trade blocked by cooldown for {symbol}")
                            return
                        logger.info(f"Opening new {action} position (reverse trading)")
                        self.record_reverse_trade(symbol)
                        new_side = "buy" if action == "BUY" else "sell"
                        new_order = kucoin.place_order(new_side, 1, self.symbol)
                        if new_order:
                            await self.send_telegram_message(f"🚀 REVERSE TRADING: Opened new {action} position")
                            self.last_action = action
                        return
            # ========== END REVERSE TRADING ==========
            
            if action in ['BUY', 'SELL'] and not has_pos and risk_res.get('can_trade'):
                size = 1
                side = "buy" if action == "BUY" else "sell"
                order = kucoin.place_order(side, size, self.symbol)
                print(f"🚀 WOULD EXECUTE: {action} at ${price:.2f}")
            if order:
                    logger.info(f"Auto trade executed: {action} at ${price:.2f}")
                    await self.send_telegram_message(f"🚀 AUTO TRADE: {action} at ${price:.2f}")
        except Exception as e:
            logger.error(f"Scheduled analysis error: {e}")

    async def send_telegram_message(self, message):
        if self.application:
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            if chat_id:
                await self.application.bot.send_message(chat_id, message, parse_mode='Markdown')

# ============================================================
# MONITORING SL/TP REAL-TIME (Setiap 10 detik)
# ============================================================


async def monitor_sltp_loop():
    logger.info("🟢 SL/TP MONITOR STARTED")
    print("🟢 SL/TP MONITOR STARTED")
    """Monitor stop loss sederhana"""
    print("🔴 SL/TP MONITOR STARTED!")
    import os
    from utils.kucoin_api import KuCoinFutures
    
    _kucoin = KuCoinFutures(
        api_key=os.getenv('KUCOIN_API_KEY'),
        api_secret=os.getenv('KUCOIN_API_SECRET'),
        api_passphrase=os.getenv('KUCOIN_API_PASSPHRASE')
    )
    
    while True:
        logger.info("🔄 SL/TP MONITOR LOOP RUNNING")
        print("🔄 SL/TP MONITOR LOOP RUNNING")
        try:
            position = _kucoin.get_position()
            if position.get('has_position'):
                entry = position.get('entry')
                current = position.get('current', entry)
                side = position.get('side')
                
                print(f"🔍 Posisi: {side} | Entry: {entry:.2f} | Current: {current:.2f}")
                
                if side == 'long':
                    sl = entry * 0.985
                    if current <= sl:
                        print(f"🔴 STOP LOSS HIT! Closing LONG at {current:.2f}")
                        _kucoin.close_position()
                else:
                    sl = entry * 1.015
                    tp = entry * 0.97
                    if current >= sl:
                        print(f"🔴 STOP LOSS HIT! Closing SHORT at {current:.2f}")
                        _kucoin.close_position()
                    elif current <= tp:
                        print(f"🎯 TAKE PROFIT HIT! Closing SHORT at {current:.2f}")
                        _kucoin.close_position()
                        
        except Exception as e:
            print(f"Error: {e}")
        
        import asyncio
        await asyncio.sleep(5)


async def scheduled_analysis():
    global trading_bot
    print("🔍 SCHEDULED ANALYSIS RUNNING")
    import sys
    sys.stdout.flush()
    await trading_bot.analyze_and_trade()

async def main():
    # Mulai scheduler pada menit ke-0 berikutnya
    from datetime import datetime, timedelta
    
    # Inisialisasi TradingBot instance
    global trading_bot
    trading_bot = TradingBot()
    
    now = datetime.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    start_seconds = (next_hour - now).total_seconds()
    trading_bot.scheduler.add_job(scheduled_analysis, 'interval', minutes=trading_bot.analysis_interval, next_run_time=datetime.now() + timedelta(seconds=start_seconds))
    trading_bot.scheduler.start()
    
    app = Application.builder().token(TOKEN).build()
    trading_bot.application = app
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.initialize()
    await app.start()
    asyncio.create_task(monitor_sltp_loop())
    await app.updater.start_polling()
    
    logger.info("Bot started with 6 agents (including Whale) and Qwen AI primary")
    await asyncio.Event().wait()



async def get_realtime_price():
    """Ambil harga real-time dari KuCoin REST API"""
    try:
        price = kucoin.get_price()
        return price
    except Exception as e:
        logger.error(f"Error getting price: {e}")
        return 0


if __name__ == "__main__":
    asyncio.run(main())

    # ========== TRAILING STOP ==========
    TRAILING_ACTIVATE_PCT = 0.015  # Aktif setelah profit 1.5%
    TRAILING_DISTANCE_PCT = 0.005  # Jarak trailing 0.5%
    
    if profit_pct >= TRAILING_ACTIVATE_PCT:
        if side == "long":
            new_sl = current * (1 - TRAILING_DISTANCE_PCT)
            if 'current_trailing_sl' not in locals() or current_trailing_sl is None or new_sl > current_trailing_sl:
                current_trailing_sl = new_sl
                logger.info(f"📈 TRAILING STOP: ${current_trailing_sl:.2f}")
        else:
            new_sl = current * (1 + TRAILING_DISTANCE_PCT)
            if 'current_trailing_sl' not in locals() or current_trailing_sl is None or new_sl < current_trailing_sl:
                current_trailing_sl = new_sl
                logger.info(f"📉 TRAILING STOP: ${current_trailing_sl:.2f}")
    
    # Cek trailing stop hit
    if 'current_trailing_sl' in locals() and current_trailing_sl:
        if (side == "long" and current <= current_trailing_sl) or (side == "short" and current >= current_trailing_sl):
            logger.info(f"🔴 TRAILING STOP HIT! Closing {side.upper()}")
            kucoin.close_position()
            current_trailing_sl = None
