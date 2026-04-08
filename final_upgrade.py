import re

with open('agents/technical_agent.py', 'r') as f:
    content = f.read()

# Cek apakah sudah ada kode perhitungan
if 'avg_atr_percent' not in content:
    # Tambahkan kode perhitungan sebelum return
    old_return = 'return {'
    new_code = '''        # ========== DYNAMIC SL CALCULATION ==========
        avg_atr_percent = 1.5
        volume_ratio_avg = 1.0
        
        if timeframe_signals:
            atr_values = []
            vol_ratios = []
            for tf_name, tf_data in timeframe_signals.items():
                if tf_data.get("atr_percent"):
                    atr_values.append(tf_data["atr_percent"])
                if tf_data.get("volume_ratio"):
                    vol_ratios.append(tf_data["volume_ratio"])
            if atr_values:
                avg_atr_percent = sum(atr_values) / len(atr_values)
            if vol_ratios:
                volume_ratio_avg = sum(vol_ratios) / len(vol_ratios)
        # ========== END ==========
        
    return {'''
    
    content = content.replace(old_return, new_code)
    
    # Update nilai di return
    content = content.replace('"atr_percent": 1.5', '"atr_percent": round(avg_atr_percent, 2)')
    content = content.replace('"volume_ratio": 1.0', '"volume_ratio": round(volume_ratio_avg, 2)')
    
    with open('agents/technical_agent.py', 'w') as f:
        f.write(content)
    print('✅ Upgrade applied')
else:
    print('Already upgraded')
