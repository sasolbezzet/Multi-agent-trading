import re

file_path = "main.py"

with open(file_path, 'r') as f:
    content = f.read()

# Cari dan ganti pattern
old = 'await trading_bot.groq.decide(technical=technical, sentiment=sentiment, news_social=news_social, risk=risk, current_price=current_price, has_position=has_position, last_action=trading_bot.last_action)'
new = 'await trading_bot.groq.decide(technical=technical, sentiment=sentiment, news_social=news_social, exchange=exchange_data, risk=risk, current_price=current_price, has_position=has_position, last_action=trading_bot.last_action)'

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w') as f:
        f.write(content)
    print("✅ Fixed decide call")
else:
    # Coba pattern lain
    old2 = 'await trading_bot.groq.decide(technical=technical,sentiment=sentiment,news_social=news_social,risk=risk,current_price=current_price,has_position=has_position,last_action=trading_bot.last_action)'
    if old2 in content:
        content = content.replace(old2, new)
        with open(file_path, 'w') as f:
            f.write(content)
        print("✅ Fixed decide call (alt pattern)")
    else:
        print("Pattern not found, searching...")
        # Tampilkan baris yang mengandung decide
        for i, line in enumerate(content.split('\n')):
            if 'groq.decide' in line:
                print(f"Line {i}: {line[:100]}")
