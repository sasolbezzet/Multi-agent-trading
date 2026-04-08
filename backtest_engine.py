#!/usr/bin/env python3
import sqlite3

class BacktestEngine:
    def __init__(self, initial_balance=1000, leverage=25):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.leverage = leverage
        self.trades = []
        self.position = None
        self.wins = 0
        self.losses = 0
    
    def run(self, days=None):
        conn = sqlite3.connect('signals.db')
        cursor = conn.cursor()
        
        if days:
            cursor.execute("SELECT timestamp, price, ai_action, ai_confidence FROM signals_history WHERE timestamp > datetime('now', ?) ORDER BY timestamp ASC", (f'-{days} days',))
        else:
            cursor.execute("SELECT timestamp, price, ai_action, ai_confidence FROM signals_history ORDER BY timestamp ASC")
        
        signals = cursor.fetchall()
        conn.close()
        
        if not signals:
            return None
        
        for signal in signals:
            ts, price, action, conf = signal
            
            if action in ['BUY', 'SELL'] and self.position is None:
                self.position = {'type': action, 'price': price, 'time': ts}
            elif action in ['BUY', 'SELL'] and self.position:
                entry = self.position['price']
                exit_price = price
                
                if self.position['type'] == 'BUY':
                    pnl_pct = (exit_price - entry) / entry * 100
                else:
                    pnl_pct = (entry - exit_price) / entry * 100
                
                pnl_usd = self.balance * 0.3 * (pnl_pct / 100) * self.leverage
                self.balance += pnl_usd
                
                if pnl_usd > 0:
                    self.wins += 1
                else:
                    self.losses += 1
                
                self.trades.append({'pnl_usd': pnl_usd, 'win': pnl_usd > 0})
                self.position = None
        
        total_return = (self.balance - self.initial_balance) / self.initial_balance * 100
        total_trades = len(self.trades)
        win_rate = self.wins / total_trades * 100 if total_trades > 0 else 0
        
        return {
            'total_return': round(total_return, 2),
            'win_rate': round(win_rate, 1),
            'total_trades': total_trades,
            'wins': self.wins,
            'losses': self.losses
        }
