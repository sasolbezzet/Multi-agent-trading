"""
Shared Telegram notification functions
"""

import os
from telegram import Bot

async def send_telegram_message(message, parse_mode='Markdown'):
    """Kirim pesan ke Telegram"""
    try:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if token and chat_id:
            bot = Bot(token=token)
            await bot.send_message(chat_id, message, parse_mode=parse_mode)
    except Exception as e:
        print(f"Telegram error: {e}")
