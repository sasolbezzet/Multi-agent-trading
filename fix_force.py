import re

file_path = "main.py"

with open(file_path, 'r') as f:
    content = f.read()

# Cari force_signal handler dan tambahkan exchange parameter
old_force = '''decision = await trading_bot.groq.decide(
            technical=technical, sentiment=sentiment, news_social=news_social,
            risk=risk, current_price=current_price,
            has_position=has_position, last_action=trading_bot.last_action
        )'''

new_force = '''decision = await trading_bot.groq.decide(
            technical=technical, sentiment=sentiment, news_social=news_social,
            exchange=exchange_data, risk=risk, current_price=current_price,
            has_position=has_position, last_action=trading_bot.last_action
        )'''

if old_force in content:
    content = content.replace(old_force, new_force)
    with open(file_path, 'w') as f:
        f.write(content)
    print("✅ Fixed force signal handler")
else:
    print("Force signal pattern not found, checking...")
    # Cari pattern dengan format berbeda
    if 'exchange_data' in content:
        print("exchange_data already in force signal")
    else:
        print("Need manual fix")

with open(file_path, 'r') as f:
    if 'exchange_data' in f.read():
        print("✅ exchange_data found in file")
