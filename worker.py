import sys
import os
import time
import requests
import json
import pandas as pd
from datetime import datetime

# ==================================================
# SYSTEM PFAD & IMPORTS
# ==================================================
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

from config.settings import HEADERS, SUPABASE_URL
from agents.gemini_agent import GeminiCoreAgent

gemini_agent = GeminiCoreAgent()

# ==================================================
# MARKTDATEN
# ==================================================
def get_live_kraken_markets():
    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        response = requests.get(url, timeout=10)
        data = response.json()
        markets = [x for x in data["result"].keys() if x.endswith("USDT")]
        return markets[:5]
    except:
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "TAOUSDT", "QNTUSDT"]

def calculate_market_metrics(pair):
    try:
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        res = requests.get(url, timeout=10).json()
        candles = list(res["result"].values())[0]
        df = pd.DataFrame(candles, columns=["time", "open", "high", "low", "close", "vwap", "volume", "count"])
        df["close"] = df["close"].astype(float)
        return {"price": float(df["close"].iloc[-1])}
    except:
        return None

# ==================================================
# TRADING ZYKLUS (MIT JSON PARSING)
# ==================================================
def run_market_cycle():
    markets = get_live_kraken_markets()
    market_data = {m: calculate_market_metrics(m) for m in markets}
    
    prompt = f"""
    Analysiere diese Märkte mathematisch.
    Antworte NUR mit reinem JSON, keine Erklärungen. 
    Format: {{"MARKTNAME": "BUY"}} oder {{"MARKTNAME": "SELL"}}
    Daten: {market_data}
    """
    
    try:
        answer = gemini_agent.execute_thought_cycle(prompt)
        
        # Sicherheits-Check gegen API-Blockaden
        if any(x in answer for x in ["Quota", "API", "error"]):
            print("⏳ KI blockiert. Warte 90s...", flush=True)
            time.sleep(90)
            return

        # JSON aus der Antwort extrahieren (falls KI Text drumherum schreibt)
        start = answer.find('{')
        end = answer.rfind('}') + 1
        json_str = answer[start:end]
        signals = json.loads(json_str)

        for market, direction in signals.items():
            if market in market_data and direction in ["BUY", "SELL"]:
                print(f"✅ Signal: {market} -> {direction}", flush=True)
                
                # Trade in Supabase schreiben
                price = market_data[market]["price"]
                trade_data = {
                    "Vermögenswert": market,
                    "Richtung": "LONG" if direction == "BUY" else "SHORT",
                    "Eintrittspreis": price,
                    "Marge in USD": 20.0,
                    "Status": "ACTIVE"
                }
                requests.post(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS, json=trade_data)

    except Exception as e:
        print(f"⚠️ Parsing-Fehler oder API-Pause: {e}", flush=True)
        time.sleep(60)

# ==================================================
# HAUPTSCHLEIFE
# ==================================================
def main():
    print("🚀 Worker gestartet", flush=True)
    while True:
        try:
            gemini_agent.process_live_chat()
            run_market_cycle()
        except Exception as e:
            print(f"Fehler: {e}", flush=True)
        time.sleep(120) # 2 Minuten Pause als Sicherheitsabstand zum API-Limit

if __name__ == "__main__":
    main()
