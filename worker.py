import sys
import os
import time
import requests
import pandas as pd
from datetime import datetime

# --- CRITICAL: PFAD-WEGWEISER ---
ZENTRALER_PFAD = os.path.dirname(os.path.abspath(__file__))
if ZENTRALER_PFAD not in sys.path:
    sys.path.insert(0, ZENTRALER_PFAD)

# --- MODULARE IMPORTS ---
from config.settings import HEADERS, SUPABASE_URL
from agents.gemini_agent import GeminiCoreAgent

# Instanziierung des zentralen KI-Gehirns
gemini_agent = GeminiCoreAgent()

def get_live_kraken_markets():
    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        res = requests.get(url, timeout=10).json()
        if "result" not in res: return ["XBTUSDT", "ETHUSDT"]
        pairs = [pair for pair in res.get("result", {}).keys() if pair.endswith("USDT")]
        return pairs[:15]
    except:
        return ["XBTUSDT", "ETHUSDT"]

def calculate_advanced_metrics(pair):
    try:
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        res = requests.get(url, timeout=10).json()
        if "result" not in res or not res["result"]: return None
            
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

def run_trading_cycle():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚙️ Starte mathematischen Marktscan...")
    märkte = get_live_kraken_markets()
    
    for markt in märkte:
        metriken = calculate_advanced_metrics(markt)
        if not metriken: continue
        
        rsi = metriken["rsi"]
        preis = metriken["live_price"]
        ema = metriken["ema"]
        
        if preis > ema and rsi < 45:
            print(f"🎯 SIGNAL GEFUNDEN FÜR {markt}! Kontaktiere Agenten für Sentiment...")
            # Das Gehirn entscheidet autonom über das Markt-Sentiment
            sentiment = gemini_agent.execute_thought_cycle(f"Analysiere das aktuelle Internet-Sentiment für {markt}. Antworte NUR mit 'BUY' oder 'HOLD'.")
            
            if "BUY" in sentiment.upper():
                print(f"🚀 Agent gibt GO! Trage Trade für {markt} ein...")
                trade_data = {
                    "Vermögenswert": markt,
                    "Richtung": "LONG",
                    "Eintrittspreis": preis,
                    "Marge in USD": 20.0,
                    "Hebelwirkung": 10,
                    "Take_Profit_Preis": round(preis * 1.03, 2),
                    "Stop_Loss_Preis": round(preis * 0.97, 2),
                    "Status": "ACTIVE",
                    "Begründung": f"KI-Entscheidung: Ausbruch über EMA20 bestätigt durch Kern-Agent.",
                    "Indikatoren_Setup": f"RSI: {rsi}, EMA: {ema}",
                    "Erwartete_Bewegung": "+3.00%"
                }
                requests.post(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS, json=trade_data)
                break

if __name__ == "__main__":
    print("🦅 KIAgent Triebwerk mit integriertem KI-Gehirn aktiv...")
    while True:
        gemini_agent.process_live_chat() # <--- HIER DECKELT JETZT DAS NEUE GEHIRN DEN CHAT
        run_trading_cycle()
        time.sleep(20)
