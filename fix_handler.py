import re

file_path = "main.py"

with open(file_path, 'r') as f:
    content = f.read()

# Perbaiki callback handler untuk force_signal
old = '''elif data == "force_signal":
        await context.bot.send_message(chat_id, "🔄 Force analyzing...", parse_mode='Markdown')
        await trading_bot.analyze_and_trade()'''

new = '''elif data == "force_signal":
        await context.bot.send_message(chat_id, "🔄 Force analyzing...", parse_mode='Markdown')
        try:
            await trading_bot.analyze_and_trade()
        except Exception as e:
            await context.bot.send_message(chat_id, f"❌ Error: {str(e)[:100]}", parse_mode='Markdown')'''

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w') as f:
        f.write(content)
    print("✅ Handler fixed")
else:
    print("Pattern not found, checking...")
    # Cari pattern alternatif
    import re
    pattern = r'elif data == "force_signal":.*?await trading_bot\.analyze_and_trade\(\)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        print(f"Found: {match.group()[:100]}")
