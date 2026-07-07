import os
import time
import requests
import pandas as pd
from datetime import datetime

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = "https://swyjycklcbcfhiafibar.supabase.co"
SUPABASE_KEY = "sb_publishable_e4pYpgdnhEEsN3iEZ6rghQ_M7IGgrl4"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

MAX_TOTAL_BUDGET_USD = 200.0  
FIXED_LEVERAGE = 10           

def get_live_kraken_markets():
    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        res = requests.get(url, timeout=10).json()
        if "result" not in res: 
            return ["XBTUSDT", "ETHUSDT"]
        return [pair for pair in res.get("result", {}).keys() if pair.endswith("USDT")][:50]
    except: 
        return ["XBTUSDT", "ETHUSDT"]

def calculate_advanced_metrics(pair):
    try:
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        res = requests.get(url, timeout=10).json()
        if "result" not in res:
            return None
            
        data_points = list(res["result"].values())[0]
        df = pd.DataFrame(data_points, columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)

        df['tr'] = df['high'] - df['low']
        atr = df['tr'].rolling(14).mean().iloc[-1]
        ema20 = df['close'].rolling(20).mean().iloc[-1]
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
        rsi = 100 - (100 / (1 + (gain / loss))) if loss > 0 else 100

        return {"live_price": df['close'].iloc[-1], "rsi": round(rsi, 2), "ema": round(ema20, 4), "atr": round(atr, 4)}
    except: 
        return None
