import os
import json
import re
import time
import ccxt
import yfinance as yf
import numpy as np
from agents.model_router import ModelRouter
from database.supabase import send_chat_message, save_trade, close_trade
from config.settings import SUPABASE_URL, HEADERS

# --- DEINE KOMPLETTE ASSET-LISTE ---
MONITORED_ASSETS = [
    "BTC-USD", "XRP-USD", "SOL-USD", "ETH-USD", "DOGE-USD", "ZEC-USD", "TRON-USD", 
    "PAXG-USD", "RENDER-USD", "FET-USD", "PEPE-USD", "QNT-USD", "WLD-USD", 
    "CHAINLINK-USD", "SUI-USD", "NILLION-USD", "TAO-USD", "MIDNIGHT-USD", 
    "SPCE", "GOOGL", "NVDA", "MRVL", "ORCL"
]

# --- HELFER: RSI BERECHNEN ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0: return 100
    rs = up / down
    return 100 - (100 / (1 + rs))

# --- HELFER: ASSET-DATEN HOLEN (5m, 15m, 1h) ---
def get_asset_data(symbol):
    try:
        if symbol in ["SPCE", "GOOGL", "NVDA", "MRVL", "ORCL"]:
            ticker = yf.Ticker(symbol)
            data_5m = ticker.history(period="2d", interval="5m")
            data_1h = ticker.history(period="5d", interval="1h")
            if data_5m.empty: return None
            last_price = data_5m['Close'].iloc[-1]
            return {
                "symbol": symbol,
                "last": last_price,
                "closes_5m": data_5m['Close'].tolist(),
                "closes_15m": data_5m.resample('15T').last()['Close'].tolist(),
                "closes_1h": data_1h['Close'].tolist()
            }
        else:
            exchange = ccxt.kraken()
            ticker = exchange.fetch_ticker(symbol.replace("-", "/"))
            ohlcv_5m = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe='5m', limit=50)
            ohlcv_1h = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe='1h', limit=50)
            return {
                "symbol": symbol,
                "last": ticker['last'],
                "closes_5m": [c[4] for c in ohlcv_5m],
                "closes_15m": [c[4] for c in ohlcv_5m], # Für Krypto nehmen wir simple 15m
                "closes_1h": [c[4] for c in ohlcv_1h]
            }
    except Exception as e:
        print(f"❌ Fehler bei {symbol}: {e}")
        return None

# --- KI ENTSCHEIDUNG (AKTIVER EINSTIEG) ---
def get_entry_decision(market_data):
    router = ModelRouter()
    rsi_5m = calculate_rsi(market_data['closes_5m'])
    rsi_15m = calculate_rsi(market_data['closes_15m'])
    rsi_1h = calculate_rsi(market_data['closes_1h'])
    
    # KRITISCH: Der Prompt zwingt ihn zum Handeln, wenn eine Konfluenz vorliegt!
    prompt = f"""
    Du bist ein professioneller, aggressiver Scalper. Dein Job ist es, täglich viele kleine Trades zu gewinnen.
    
    Marktdaten für {market_data['symbol']}:
    - Aktueller Kurs: {market_data['last']}
    - 5m RSI: {rsi_5m:.1f}
    - 15m RSI: {rsi_15m:.1f}
    - 1h RSI: {rsi_1h:.1f}
    
    DEINE AUFGABE:
    Suche aktiv nach Setups. 
    - Wenn 5m RSI unter 30 liegt UND der 1h RSI neutral oder über 50 ist -> **BUY**.
    - Wenn 5m RSI über 70 liegt UND der 1h RSI neutral oder unter 50 ist -> **SELL**.
    - Wenn die 15m und 1h RSI beide gleiche Richtung zeigen, bestätigt das den Trade.
    - Ansonsten **HOLD**.
    
    Denke daran: Verluste gehören dazu, aber wir steigen schnell aus (Scalping).
    Antworte NUR im JSON-Format:
    {{"decision": "BUY" oder "SELL" oder "HOLD", "reasoning": "Begründung", "stop_loss": 0.0, "take_profit": 0.0}}
    """
    answer, _ = router.route(prompt, system_context="Du antwortest NUR mit JSON.", preferred_model="groq")
    match = re.search(r'\{.*\}', answer, re.DOTALL)
    if match:
        try: return json.loads(match.group(0))
        except: pass
    return {"decision": "HOLD", "reasoning": "Fehler im JSON", "stop_loss": 0.0, "take_profit": 0.0}

# --- NEU: POST-TRADE ANALYSE (DER BOT LERNT AUS JEDEM TRADE) ---
def analyze_learn(asset, entry_price, exit_price, pnl, reasoning):
    profit_text = "GEWINN" if pnl > 0 else "VERLUST"
    
    prompt = f"""
    Ich habe gerade einen Trade auf {asset} mit einem {profit_text} von ${pnl:.2f} abgeschlossen.
    Einstiegspreis: {entry_price}, Ausstiegspreis: {exit_price}.
    Meine ursprüngliche Begründung: {reasoning}.
    
    Aufgabe: Analysiere diesen Trade. Warum habe ich gewonnen/verloren?
    Lehre mich etwas Neues daraus. Was hätte ich besser machen können?
    Antworte in einem kurzen, lehrreichen Satz auf Deutsch.
    """
    
    router = ModelRouter()
    answer, _ = router.route(prompt, system_context="Du bist ein erfahrener Trading-Coach.", preferred_model="groq")
    
    # Speichere die Lektion im Gedächtnis (als System-Nachricht, damit das Dashboard es anzeigt)
    send_chat_message("system", f"📘 Lektion aus dem {profit_text}: {answer}")

# --- HAUPTLOOP ---
def main_loop():
    print("🧠 KI-Profi-Trader gestartet (Aggressiver Scalping-Modus). 24/7 aktiv.", flush=True)
    from agents.gemini_agent import GeminiCoreAgent
    agent = GeminiCoreAgent()
    last_chat_id = 0

    while True:
        try:
            for symbol in MONITORED_ASSETS:
                data = get_asset_data(symbol)
                if not data: continue
                
                # Prüfen: Haben wir eine offene Position?
                active_trades = requests.get(
                    f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id,Eintrittspreis&Vermögenswert=eq.{symbol}&Status=eq.ACTIVE",
                    headers=HEADERS
                ).json()
                
                has_position = len(active_trades) > 0
                entry_price = float(active_trades[0]['Eintrittspreis']) if has_position else 0.0
                trade_id = active_trades[0]['id'] if has_position else 0
                
                rsi_5m = calculate_rsi(data['closes_5m'])
                rsi_15m = calculate_rsi(data['closes_15m'])
                
                # EXIT: Wenn wir drin sind und der 5m/15m RSI über 70 steigt -> SOFORT RAUS
                if has_position:
                    if rsi_5m > 70 or rsi_15m > 70:
                        pnl = data['last'] - entry_price
                        close_trade(symbol, data['last'], pnl)
                        send_chat_message("system", f"⚡ {symbol}: Blitz-Exit! RSI {rsi_5m:.1f}. PnL: ${pnl:.2f}")
                        # JETZT LERNT ER SOFORT DARAUS
                        analyze_learn(symbol, entry_price, data['last'], pnl, "RSI Overbought Exit")
                        continue
                
                # ENTRY: Wenn wir KEINE Position haben, sucht er aggressiv
                elif not has_position:
                    decision = get_entry_decision(data)
                    if decision['decision'] in ['BUY', 'SELL']:
                        save_trade(
                            asset=symbol,
                            direction=decision['decision'],
                            entry_price=data['last'],
                            stop_loss=decision.get('stop_loss', 0.0),
                            take_profit=decision.get('take_profit', 0.0),
                            reasoning=decision.get('reasoning', 'Aggressive Scalping'),
                            indicators=f"5m RSI: {rsi_5m:.1f}, 15m RSI: {rsi_15m:.1f}",
                            expected_move='Scalping',
                            status='ACTIVE'
                        )
                        send_chat_message("system", f"🟢 Einstieg {symbol}: {decision['decision']} bei {data['last']}. Grund: {decision['reasoning']}")
            
            # Chat
            if int(time.time()) % 5 == 0:
                new_id = agent.process_live_chat(last_chat_id)
                if new_id is not None: last_chat_id = new_id

            time.sleep(1) # Blitzschnelle Überprüfung
        except Exception as e:
            print(f"❌ Fehler im Hauptloop: {e}", flush=True)
            time.sleep(10)

if __name__ == "__main__":
    main_loop()
