import os
from datetime import datetime, timedelta
from backtest_metrics import BacktestMetrics

class RiskAgent:


    async def _get_guavy_backtest(self):
        """Ambil backtest summary dari Guavy API untuk BTC"""
        try:
            import requests
            import os
            
            env_path = '/home/ubuntu/groq_trading_bot/.env'
            with open(env_path) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
            
            api_key = os.getenv('GUAVY_API_KEY')
            if not api_key:
                return None
            
            url = "https://data.guavy.com/api/v1/trades/get-backtest-summary/BTC/momentum"
            headers = {"Authorization": f"Bearer {api_key}"}
            params = {"years": 1}
            
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "win_rate": data.get('profitable_trade_percent'),
                    "total_return": data.get('profit_percent'),
                    "annualized_return": data.get('annualized_return'),
                    "average_profit": data.get('average_profit'),
                    "average_loss": data.get('average_loss'),
                    "average_profit_percent": data.get('average_profit_percent'),
                    "average_loss_percent": data.get('average_loss_percent'),
                    "max_drawdown": data.get('peak_loss'),
                    "total_trades": data.get('total_trades'),
                    "profitable_trades": data.get('profitable_trades'),
                    "unprofitable_trades": data.get('unprofitable_trades'),
                    "start_date": data.get('start_date'),
                    "end_date": data.get('end_date'),
                    "source": "Guavy"
                }
        except Exception as e:
            print(f"Guavy backtest error: {e}")
        return None

    def __init__(self, stop_loss_pct=0.015, take_profit_pct=0.03):
        self.name = "Risk Manager"
        self.default_stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        # Default values
        self.min_confidence = 60
        self.cooldown_minutes = 60
        self.daily_loss_limit = 5.0
        self.min_volume_ratio = 1.2
        self.max_atr_percent = 5.0  # Maksimal ATR 5% (volatilitas ekstrem)
        
        # Tracking
        self.daily_loss = 0.0
        self.last_loss_time = None
        self.last_reset_date = None
        
        # Backtesting adjustment
        self.backtest_metrics = BacktestMetrics()
    
    async def analyze(self, balance, has_position, current_position=None, atr_percent=None, volume_ratio=None):
        result = {
            "agent": self.name,
            "can_trade": True,
            "risk_score": 0,
            "reason": "OK"
        }
        
        # Adjust confidence based on backtesting
        try:
            perf = self.backtest_metrics.get_recent_performance(7)
            if perf:
                if perf['is_profitable'] and perf['win_rate'] > 55:
                    # Bot performing well, can be more aggressive
                    self.min_confidence = 55
                    result['backtest_adjustment'] = 'aggressive'
                elif perf['is_profitable'] is False and perf['win_rate'] < 40:
                    # Bot performing poorly, be more conservative
                    self.min_confidence = 70
                    result['backtest_adjustment'] = 'conservative'
                else:
                    self.min_confidence = 60
                    result['backtest_adjustment'] = 'normal'
        except:
            self.min_confidence = 60
        
        result["min_confidence_required"] = self.min_confidence
        
        # Reset daily loss counter
        today = datetime.now().date()
        if self.last_reset_date != today:
            self.daily_loss = 0.0
            self.last_reset_date = today
        
        # Check volume
        if volume_ratio is not None:
            result["volume_ratio"] = volume_ratio
            if volume_ratio < self.min_volume_ratio:
                result["can_trade"] = False
                result["risk_score"] = 100
                result["reason"] = f"Low volume: {volume_ratio:.1f}x"
                return result
        
        # Check volatility (ATR terlalu tinggi)
        if atr_percent is not None:
            result["atr_percent"] = atr_percent
            if atr_percent > self.max_atr_percent:
                result["can_trade"] = False
                result["risk_score"] = 100
                result["reason"] = f"Extreme volatility: ATR {atr_percent:.1f}% > {self.max_atr_percent}%"
                return result
            elif atr_percent > self.max_atr_percent * 0.7:
                result["warning"] = f"High volatility: ATR {atr_percent:.1f}%"
        
        # Check cooldown
        if self.last_loss_time:
            cooldown_end = self.last_loss_time + timedelta(minutes=self.cooldown_minutes)
            if datetime.now() < cooldown_end:
                result["can_trade"] = False
                result["risk_score"] = 100
                result["reason"] = f"Cooldown active"
                return result
        
        # Check daily loss
        if self.daily_loss >= self.daily_loss_limit:
            result["can_trade"] = False
            result["risk_score"] = 100
            result["reason"] = f"Daily loss limit reached"
            return result
        
        # Dynamic SL
        if atr_percent and atr_percent > 0:
            dynamic_sl = min(max(atr_percent * 1.5, 0.8), 3.0)
            result["stop_loss_pct"] = dynamic_sl / 100
            result["stop_loss_type"] = "dynamic_atr"
        else:
            result["stop_loss_pct"] = self.default_stop_loss_pct
            result["stop_loss_type"] = "fixed"
        
        result["take_profit_pct"] = self.take_profit_pct
        
        # Balance check
        min_margin = 2.66
        if balance < min_margin:
            result["can_trade"] = False
            result["risk_score"] = 100
            result["reason"] = f"Insufficient balance: ${balance:.2f}"
        elif balance < min_margin * 3:
            result["risk_score"] = 60
        elif balance < min_margin * 5:
            result["risk_score"] = 30
        else:
            result["risk_score"] = 10
        
        if has_position:
            result["can_trade"] = False
            result["reason"] = "Position already open"
        
        return result
    
    def calculate_sl_tp(self, price, action, atr_percent=None):
        if atr_percent and atr_percent > 0:
            sl_pct = min(max(atr_percent * 1.5, 0.8), 3.0) / 100
        else:
            sl_pct = self.default_stop_loss_pct
        
        if action == "BUY":
            sl = price * (1 - sl_pct)
            tp = price * (1 + self.take_profit_pct)
        else:
            sl = price * (1 + sl_pct)
            tp = price * (1 - self.take_profit_pct)
        
        return round(sl, 2), round(tp, 2)
