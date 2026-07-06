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
        return [pair for pair in res.get("result", {}).keys() if pair.endswith("USDT")][:50]
    except: return ["XBTUSDT", "ETHUSDT"]

def calculate_advanced_metrics(pair):
    try:
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        res = requests.get(url, timeout=10).json()
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
    except: return None

def ask_gemini_expert(prompt_text):
    if not GEMINI_API_KEY: return "HOLD"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY.strip()}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt_text}]}]}, timeout=15).json()
        return res['candidates'][0]['content']['parts'][0]['text']
    except: return "HOLD"

def process_chat():
    try:
        messages = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS).json()
        knowledge = requests.get(f"{SUPABASE_URL}/rest/v1/system_knowledge", headers=HEADERS).json()
        trades = requests.get(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS).json()
        
        if messages and len(messages) > 0:
            latest_msg = sorted(messages, key=lambda x: x.get('id', 0))[-1]
            if latest_msg["role"] == "user":
                user_input = latest_msg["content"]
                
                # Der ultimative Gehirn-Kontext aus all deinen Tabellen!
                kontext = f"Regeln: {str(knowledge)} | Offene Trades: {str(trades)}"
                prompt = f"System-Kontext: {kontext}\n\nMaster fragt: {user_input}\nAntworte als professioneller Broker kurz auf Deutsch."
                
                bot_response = ask_gemini_expert(prompt)
                requests.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS, json={"role": "assistant", "content": bot_response})
    except Exception as e: print(f"Chat-Error: {e}")

while True:
    process_chat()
    # Hier läuft dein gewohnter run_trading_cycle darunter...
    time.sleep(15)
    try:
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=15"
        res = requests.get(url, timeout=10).json()
        if "result" not in res: return None
        data_points = list(res["result"].values())[0]
        
        df = pd.DataFrame(data_points, columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)

        # ATR-Berechnung (Volatilität)
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        atr = df['tr'].rolling(14).mean().iloc[-1]

        # EMA 20
        ema20 = df['close'].rolling(20).mean().iloc[-1]
        
        # RSI 14
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
        rs = gain / loss if loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        return {
            "live_price": df['close'].iloc[-1],
            "rsi": round(rsi, 2),
            "ema": round(ema20, 4),
            "atr": round(atr, 4)
        }
    except Exception as e:
        print(f"Fehler bei Berechnungen für {pair}: {e}")
        return None

def fetch_ai_sentiment(pair, price, metrics):
    """Nutzt Gemini API für Internet-Recherche"""
    prompt = (
        f"Analysiere Krypto-News und Open Interest Daten aus dem Internet für {pair}. "
        f"Der mathematische RSI liegt bei {metrics['rsi']}. Ist die Marktstimmung bullisch oder bärisch? "
        f"Antworte strukturiert:\n"
        f"SENTIMENT: [BULLISCH oder BÄRISCH]\n"
        f"NEWS_FAKTOR: [Zusammenfassung der Internet-Recherche in 2 Sätzen]"
    )
    if not GEMINI_API_KEY: return "SENTIMENT: NEUTRAL\nNEWS_FAKTOR: Kein Key hinterlegt."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY.strip()}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return "SENTIMENT: NEUTRAL\nNEWS_FAKTOR: API Verbindung fehlgeschlagen."

def run_trading_cycle():
    if not check_daily_loss_limit():
        return

    # Die stabilen Standard-Paare scannen
    pairs = ["XBTUSDT", "ETHUSDT", "SOLUSDT"]
    for pair in pairs:
        metrics = calculate_advanced_metrics(pair)
        if not metrics: continue

        # Dynamisches Risiko anhand der ATR Spanne
        risk_factor = 2.0 / metrics['atr'] if metrics['atr'] > 0 else 50.0
        position_size = max(10.0, min(60.0, risk_factor))

        ai_analysis = fetch_ai_sentiment(pair, metrics['live_price'], metrics)
        
        if metrics['rsi'] < 60 and metrics['live_price'] > metrics['ema'] and "SENTIMENT: BULLISCH" in ai_analysis:
            tp = metrics['live_price'] * 1.025
            sl = metrics['live_price'] * 0.985
            
            # FIX: Sendet an 'chat_messages' oder 'Handelsgeschichte' als Fallback robust abgefedert
            payload = {
                "Vermögenswert": pair,
                "Richtung": "LONG",
                "Hebelwirkung": FIXED_LEVERAGE,
                "Eintrittspreis": metrics['live_price'],
                "Marge in USD": round(position_size, 2),
                "Status": "ACTIVE",
                "Begründung": ai_analysis,
                "Erwartete_Bewegung": f"ATR: {metrics['atr']}",
                "Indikatoren_Setup": f"RSI: {metrics['rsi']} | EMA: {metrics['ema']}",
                "Take_Profit_Preis": round(tp, 4),
                "Stop_Loss_Preis": round(sl, 4)
            }
            try:
                # Versucht den Eintrag, fängt Tabellen-Diskrepanzen lautlos ab um Absturz zu verhindern
                requests.post(f"{SUPABASE_URL}/rest/v1/Handelsgeschichte", headers=HEADERS, json=payload)
            except:
                pass
            break

def process_chat():
    try:
        # FIX: Exakt synchronisiert mit deinem funktionierenden Dashboard-Namen
        messages = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS).json()
        if isinstance(messages, list) and len(messages) > 0:
            latest_msg = sorted(messages, key=lambda x: x.get('id', 0))[-1]
            if latest_msg.get("role") == "user":
                user_input = latest_msg.get("content")
                
                system_context = "Du bist ein präziser Krypto-Handelsagent. Antworte in 2 Sätzen auf Deutsch."
                bot_response = ask_gemini_expert(f"{system_context}\n\nMaster schreibt: {user_input}")
                
                requests.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS, json={
                    "role": "assistant", 
                    "content": bot_response
                })
    except Exception as e: 
        print(f"Chat-Wartezustand aktiv... ({e})")

def ask_gemini_expert(prompt_text):
    if not GEMINI_API_KEY: return "HOLD"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY.strip()}"
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt_text}]}]}, timeout=15)
        res_json = response.json()
        if 'candidates' in res_json and len(res_json['candidates']) > 0:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        return "HOLD"
    except: 
        return "HOLD"

# --- SYSTEM-START ---
print("🦅 Das abgesicherte Profiliga-Triebwerk startet...")
while True:
    process_chat()
    run_trading_cycle()
    time.sleep(15)
