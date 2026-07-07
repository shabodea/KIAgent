import sys
import os
import time
import requests
import pandas as pd
from datetime import datetime

# ==================================================
# SYSTEM PFAD
# ==================================================

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

# ==================================================
# IMPORTS
# ==================================================

from config.settings import HEADERS, SUPABASE_URL
from agents.gemini_agent import GeminiCoreAgent

# ==================================================
# KI INITIALISIEREN
# ==================================================

print("🦅 Initialisiere KI-Agent...", flush=True)
gemini_agent = GeminiCoreAgent()
print("✅ Gemini-Agent geladen", flush=True)

# ==================================================
# MARKTDATEN
# ==================================================

def get_live_kraken_markets():
    try:
        url = "https://api.kraken.com/0/public/AssetPairs"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "result" not in data:
            return ["TAOUSDT", "QNTUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT"]

        markets = [x for x in data["result"].keys() if x.endswith("USDT")]
        return markets[:30] # Wir ziehen 30 Märkte für den Durchlauf

    except Exception as e:
        print(f"❌ Kraken Fehler: {e}", flush=True)
        return ["TAOUSDT", "QNTUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT"]

def calculate_market_metrics(pair):
    try:
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "result" not in data:
            return None

        candles = list(data["result"].values())[0]
        df = pd.DataFrame(candles, columns=["time", "open", "high", "low", "close", "vwap", "volume", "count"])
        
        df["close"] = df["close"].astype(float)
        df["ema20"] = df["close"].rolling(20).mean()

        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        
        rsi = (100 - (100 / (1 + gain.iloc[-1] / loss.iloc[-1]))) if loss.iloc[-1] != 0 else 100

        return {
            "price": float(df["close"].iloc[-1]),
            "ema": float(df["ema20"].iloc[-1]),
            "rsi": round(float(rsi), 2)
        }
    except:
        return None

# ==================================================
# TRADING ZYKLUS (BATCH-TRAINING MODE)
# ==================================================

def run_market_cycle():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 Starte BATCH-SCAN...", flush=True)

    all_markets = get_live_kraken_markets()
    
    # Wir nehmen uns 10 Märkte für dieses eine Paket (1 API-Request)
    batch_markets = all_markets[:10] 
    market_data_map = {}
    prompt_lines = [
        "Trainings-Modus aktiv. Hier sind die Indikatoren für mehrere Märkte.",
        "ZWINGENDE ANWEISUNG: Ignoriere alte Regeln. Du DARFST NICHT 'HOLD' sagen.",
        "Entscheide für JEDEN Markt zwingend auf 'BUY' oder 'SELL'.",
        "Antworte EXAKT in diesem Format pro Zeile: MARKTNAME: BUY oder SELL - Kurze Begründung\n",
        "Daten:"
    ]

    print(f"📊 Sammle Daten für {len(batch_markets)} Märkte (Free-Tier Optimierung)...", flush=True)

    for market in batch_markets:
        metrics = calculate_market_metrics(market)
        if metrics:
            market_data_map[market] = metrics
            prompt_lines.append(f"{market} - Preis: {metrics['price']}, RSI: {metrics['rsi']}, EMA20: {metrics['ema']}")

    if not market_data_map:
        return

    print("🧠 Sende gesamtes Paket an die KI (1 API Request)...", flush=True)
    batch_prompt = "\n".join(prompt_lines)
    
    # Eine einzige Anfrage für 10 Märkte!
    answer = gemini_agent.execute_thought_cycle(batch_prompt)
    
    print("\n🤖 KI antwortet:")
    trades_geöffnet = 0

    # Wir werten die Antwort zeilenweise aus
    for line in answer.split('\n'):
        if ":" in line and ("BUY" in line.upper() or "SELL" in line.upper()):
            parts = line.split(":", 1)
            market_name = parts[0].strip()
            
            if market_name in market_data_map:
                decision_text = parts[1].strip()
                metrics = market_data_map[market_name]
                price = metrics["price"]
                
                richtung = "LONG" if "BUY" in decision_text.upper() else "SHORT"
                
                print(f" ✅ {market_name}: {richtung} erkannt. Speichere...", flush=True)
                
                trade_data = {
                    "Vermögenswert": market_name,
                    "Richtung": richtung,
                    "Eintrittspreis": price,
                    "Marge in USD": 20.0,
                    "Hebelwirkung": 1,
                    "Take_Profit_Preis": round(price * 1.05 if richtung == "LONG" else price * 0.95, 2),
                    "Stop_Loss_Preis": round(price * 0.97 if richtung == "LONG" else price * 1.03, 2),
                    "Status": "ACTIVE",
                    "Begründung": decision_text,
                    "Indikatoren_Setup": f"RSI: {metrics['rsi']}, EMA: {metrics['ema']}",
                    "Erwartete_Bewegung": "Batch-Training"
                }
                
                requests.post(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS, json=trade_data)
                trades_geöffnet += 1

    print(f"🏁 BATCH BEENDET. {trades_geöffnet} neue Trades gespeichert.", flush=True)

# ==================================================
# HAUPTSCHLEIFE
# ==================================================

def main():
    print("🔥 KIAgent Worker im FREE-TIER MAXIMUM MODE gestartet", flush=True)

    while True:
        try:
            print("💬 Prüfe Chat...", flush=True)
            gemini_agent.process_live_chat()
            
            run_market_cycle()

        except Exception as e:
            print(f"🔥 Worker Fehler: {e}", flush=True)

        # Die absolute Sicherheitsbremse für den Free-Tier:
        # Garantiert, dass der Google-Zähler wieder auf 0 steht!
        time.sleep(65) 

if __name__ == "__main__":
    main()
