import sqlite3
import json
from datetime import datetime

DB_PATH = "/home/ubuntu/groq_trading_bot/trades.db"

def init_db():
    """Inisialisasi database jika belum ada"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabel trades
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            action TEXT,
            side TEXT,
            price REAL,
            size INTEGER,
            pnl REAL,
            reason TEXT,
            ai_used TEXT
        )
    ''')
    
    # Tabel sinyal (untuk analisis)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            technical TEXT,
            sentiment TEXT,
            news TEXT,
            exchange TEXT,
            whale TEXT,
            risk TEXT,
            final_action TEXT,
            final_confidence INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def save_trade(action, side, price, size, pnl, reason, ai_used):
    """Menyimpan eksekusi trade ke database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (timestamp, action, side, price, size, pnl, reason, ai_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now(), action, side, price, size, pnl, reason, ai_used))
        conn.commit()
        conn.close()
        print(f"✅ Trade saved: {action} {side} at ${price}")
        return True
    except Exception as e:
        print(f"Error saving trade: {e}")
        return False

def save_signal(technical, sentiment, news, exchange, whale, risk, final_action, final_confidence):
    """Menyimpan sinyal lengkap ke database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO signals (timestamp, technical, sentiment, news, exchange, whale, risk, final_action, final_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now(), 
              json.dumps(technical), 
              json.dumps(sentiment),
              json.dumps(news),
              json.dumps(exchange),
              json.dumps(whale),
              json.dumps(risk),
              final_action, 
              final_confidence))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving signal: {e}")
        return False

def get_trade_history(limit=50):
    """Mengambil riwayat trade"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, action, side, price, pnl, reason 
            FROM trades 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"Error getting history: {e}")
        return []

def get_performance_summary():
    """Mendapatkan ringkasan performa"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Total trades
        cursor.execute("SELECT COUNT(*) FROM trades")
        total_trades = cursor.fetchone()[0]
        
        # Win rate
        cursor.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0")
        winning_trades = cursor.fetchone()[0]
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Total PnL
        cursor.execute("SELECT SUM(pnl) FROM trades")
        total_pnl = cursor.fetchone()[0] or 0
        
        # Best trade
        cursor.execute("SELECT MAX(pnl) FROM trades")
        best_trade = cursor.fetchone()[0] or 0
        
        # Worst trade
        cursor.execute("SELECT MIN(pnl) FROM trades")
        worst_trade = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "best_trade": round(best_trade, 2),
            "worst_trade": round(worst_trade, 2)
        }
    except Exception as e:
        print(f"Error getting summary: {e}")
        return {}

# Inisialisasi database saat import
init_db()

def save_signal_to_db(price, technical, sentiment, news_social, exchange, whale, risk, decision):
    """Simpan sinyal lengkap ke database"""
    try:
        import sqlite3
        conn = sqlite3.connect('/home/ubuntu/groq_trading_bot/signals.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO signals_history (
                timestamp, price,
                technical_signal, technical_confidence,
                sentiment_signal, sentiment_confidence,
                news_signal, news_confidence,
                exchange_signal, exchange_confidence,
                whale_signal, whale_confidence,
                risk_can_trade,
                ai_action, ai_confidence, ai_reason, ai_used
            ) VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            price,
            technical.get('signal'), technical.get('confidence'),
            sentiment.get('signal'), sentiment.get('confidence'),
            news_social.get('signal'), news_social.get('confidence'),
            exchange.get('signal'), exchange.get('confidence'),
            whale.get('signal'), whale.get('confidence'),
            1 if risk.get('can_trade') else 0,
            decision.get('action'), decision.get('confidence'), decision.get('reason'), decision.get('ai_used')
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving signal: {e}")
        return False

def get_signal_stats():
    """Dapatkan statistik sinyal"""
    try:
        import sqlite3
        conn = sqlite3.connect('/home/ubuntu/groq_trading_bot/signals.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM signals_history")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM signals_history WHERE date(timestamp) = date('now')")
        today = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM signals_history WHERE ai_action = 'BUY'")
        buys = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM signals_history WHERE ai_action = 'SELL'")
        sells = cursor.fetchone()[0]
        conn.close()
        return total, today, buys, sells
    except:
        return 0, 0, 0, 0
