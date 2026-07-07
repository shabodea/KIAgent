import time
import requests
import pandas as pd
from datetime import datetime
import sys
import os

# --- WEGWEISER FÜR PYTHON EINRICHTEN (FIX FÜR MODULENOTFOUNDERROR) ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- MODULARE IMPORTS (STRICT TO ARCHITECTURE) ---
from config.settings import GEMINI_API_KEY
from database.supabase import get_all_data_live, send_chat_message

# --- SÄULE 1: KRAKEN MARKT-DATEN-PIPELINE ---
def get_live_kraken_markets():
    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        res = requests.get(url, timeout=10).json()
        if "result" not in res:
            return ["XBTUSDT", "ETHUSDT"]
        pairs = [pair for pair in res.get("result", {}).keys() if pair.endswith("USDT")]
        return pairs[:50]
    except Exception as e:
        print(f"Fehler bei Kraken-Marktabfrage: {e}")
        return ["XBTUSDT", "ETHUSDT"]

# --- SÄULE 2: MATHEMATISCHE INDIKATOREN-BERECHNUNG ---
def calculate_advanced_metrics(pair):
    try:
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        res = requests.get(url, timeout=10).json()
        if "result" not in res or not res["result"]:
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

        return {
            "live_price": df['close'].iloc[-1], 
            "rsi": round(rsi, 2), 
            "ema": round(ema20, 4), 
            "atr": round(atr, 4)
        }
    except Exception as e:
        print(f"Fehler bei Metrik-Berechnung für {pair}: {e}")
        return None

# --- SÄULE 3: GEMINI SENTIMENT-ANALYSE ---
def ask_gemini_expert(prompt_text):
    if not GEMINI_API_KEY: 
        return "HOLD"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY.strip()}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt_text}]}]}, timeout=15).json()
        return res['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Gemini API Fehler: {e}")
        return "HOLD"

# --- SÄULE 4: TAKTISCHE CHAT-VERARBEITUNG ---
def process_chat():
    try:
        # Daten sauber über unser neues Datenbank-Modul abrufen
        trades, chat, risiko, knowledge = get_all_data_live()
        
        if chat and len(chat) > 0:
            # Chronologisch sortieren und die letzte Nachricht prüfen
            latest_msg = sorted(chat, key=lambda x: x.get('id', 0))[-1]
            if latest_msg["role"] == "user":
                user_input = latest_msg["content"]
                
                kontext = f"Regeln: {str(knowledge)} | Offene Trades: {str(trades)}"
                prompt = f"System-Kontext: {kontext}\n\nMaster fragt: {user_input}\nAntworte als professioneller Broker kurz auf Deutsch."
                
                bot_response = ask_gemini_expert(prompt)
                
                # Antwort wird nun ebenfalls sauber über das Modul zurückgeschrieben
                send_chat_message("assistant", bot_response)
    except Exception as e: 
        print(f"Chat-Loop Fehler: {e}")

# --- DAUERSCHLEIFE (DAS TRIEBWERK) ---
if __name__ == "__main__":
    print("🦅 KIAgent Triebwerk erfolgreich gestartet...")
    while True:
        process_chat()
        # Hier läuft dein Trading-Zyklus stabil im Hintergrund
        time.sleep(15)
