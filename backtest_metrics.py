#!/usr/bin/env python3
"""
Mendapatkan metrik backtesting untuk dipertimbangkan oleh AI
"""

import sqlite3
from datetime import datetime, timedelta

class BacktestMetrics:
    def __init__(self):
        self.conn = sqlite3.connect('signals.db')
        self.cursor = self.conn.cursor()
    
    def get_recent_performance(self, days=7):
        """Dapatkan performa dalam X hari terakhir"""
        try:
            self.cursor.execute('''
                SELECT timestamp, price, ai_action, ai_confidence 
                FROM signals_history 
                WHERE timestamp > datetime('now', ?) 
                AND ai_action IN ('BUY', 'SELL')
                ORDER BY timestamp ASC
            ''', (f'-{days} days',))
            signals = self.cursor.fetchall()
            
            if not signals:
                return None
            
            # Simulasi sederhana
            balance = 1000
            position = None
            wins = 0
            losses = 0
            
            for ts, price, action, conf in signals:
                if action in ['BUY', 'SELL'] and position is None:
                    position = {'type': action, 'price': price}
                elif action in ['BUY', 'SELL'] and position:
                    entry = position['price']
                    if position['type'] == 'BUY':
                        pnl_pct = (price - entry) / entry * 100
                    else:
                        pnl_pct = (entry - price) / entry * 100
                    
                    pnl_usd = balance * 0.3 * (pnl_pct / 100) * 25
                    balance += pnl_usd
                    
                    if pnl_usd > 0:
                        wins += 1
                    else:
                        losses += 1
                    
                    position = None
            
            total_return = (balance - 1000) / 1000 * 100
            win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
            
            return {
                'total_return': round(total_return, 2),
                'win_rate': round(win_rate, 1),
                'total_trades': wins + losses,
                'wins': wins,
                'losses': losses,
                'period_days': days,
                'is_profitable': total_return > 0,
                'is_good_win_rate': win_rate > 50
            }
        except Exception as e:
            return None
    
    def get_signal_accuracy(self):
        """Dapatkan akurasi sinyal berdasarkan backtesting"""
        results = []
        for days in [1, 3, 7, 14, 30]:
            perf = self.get_recent_performance(days)
            if perf:
                results.append(perf)
        
        if not results:
            return None
        
        # Rata-rata performa
        avg_return = sum(r['total_return'] for r in results) / len(results)
        avg_win_rate = sum(r['win_rate'] for r in results) / len(results)
        
        return {
            'avg_return': round(avg_return, 2),
            'avg_win_rate': round(avg_win_rate, 1),
            'trend': 'improving' if results[0]['total_return'] < results[-1]['total_return'] else 'declining',
            'sample_size': len(results)
        }
    
    def close(self):
        self.conn.close()
