async def force_signal_handler(trading_bot, chat_id, context):
    try:
        current_price = trading_bot.kucoin.get_price(trading_bot.symbol)
        balance = trading_bot.kucoin.get_balance()
        position = trading_bot.kucoin.get_position(trading_bot.symbol)
        has_position = position['has_position']
        
        technical = await trading_bot.technical.analyze()
        sentiment = await trading_bot.sentiment.analyze()
        news_social = await trading_bot.news_social.analyze()
        exchange_data = await trading_bot.exchange.analyze()
        risk = await trading_bot.risk.analyze(balance, has_position, position if has_position else None)
        
        decision = await trading_bot.groq.decide(
            technical=technical, sentiment=sentiment, news_social=news_social,
            exchange=exchange_data, risk=risk, current_price=current_price,
            has_position=has_position, last_action=trading_bot.last_action
        )
        
        action = decision.get('action', 'HOLD')
        confidence = decision.get('confidence', 50)
        reason = decision.get('reason', 'No reason')
        
        msg = "ANALYSIS RESULT\n"
        msg += "------------------------\n"
        msg += f"Technical: {technical['signal']} ({technical['confidence']}%)\n"
        msg += f"Sentiment: {sentiment['signal']} ({sentiment['confidence']}%)\n"
        msg += f"News/Social: {news_social['signal']} ({news_social['confidence']}%)\n"
        msg += f"Exchange: {exchange_data['signal']} ({exchange_data['confidence']}%)\n"
        msg += f"Risk: can_trade={risk.get('can_trade', False)}\n"
        msg += "------------------------\n"
        msg += f"Groq Decision: {action} ({confidence}%)\n"
        msg += f"Reason: {reason}\n"
        msg += f"Price: ${current_price:.2f}\n"
        
        if has_position:
            msg += "------------------------\n"
            msg += "WARNING: Position already open\n"
            msg += f"Side: {position['side']}\n"
            msg += f"Entry: ${position['entry']:.2f}\n"
            msg += f"Current: ${position['current']:.2f}\n"
            msg += f"PnL: {position['pnl']:+.2f} USDT"
        
        await context.bot.send_message(chat_id, msg)
    except Exception as e:
        await context.bot.send_message(chat_id, f"Error: {str(e)[:200]}")
