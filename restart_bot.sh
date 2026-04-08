#!/bin/bash
cd /home/ubuntu/groq_trading_bot
source venv/bin/activate

if ! pgrep -f "python3 main.py" > /dev/null; then
    echo "$(date): Bot tidak berjalan, restarting..." >> bot_restart.log
    pkill -9 -f python3
    rm -f /tmp/*.lock
    nohup python3 main.py > bot.log 2>&1 &
    echo "$(date): Bot restarted with PID: $!" >> bot_restart.log
fi
