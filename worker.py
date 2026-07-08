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

# --- HELFER: EINZELNE ASSET-DATEN HOLEN (inkl. RSI für Exit) ---
def get_asset_data(symbol):
    try:
        if symbol in ["SPCE", "GOOGL", "NVDA", "MRVL", "ORCL"]:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="2d", interval="5m")
            if data.empty: return None
            last_price = data['Close'].iloc[-1]
            closes_5m = data['Close'].tolist()
            # 15m holen wir über Resampling (einfach, spart API-Calls)
            data_15m = data.resample('15T').last()
            closes_15m = data_15m['Close'].tolist()
            return {"symbol": symbol, "last": last_price, "closes_5m": closes_5m, "closes_15m": closes_15m}
        else:
            exchange = ccxt.kraken()
            ticker = exchange.fetch_ticker(symbol.replace("-", "/"))
            ohlcv_5m = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe='5m', limit=50)
            ohlcv_15m = exchange.fetch_ohlcv(symbol.replace("-", "/"), timeframe='15m', limit=50)
            return {
                "symbol": symbol,
                "last": ticker['last'],
                "closes_5m": [c[4] for c in ohlcv_5m],
                "closes_15m": [c[4] for c in ohlcv_15m]
            }
    except Exception as e:
        print(f"❌ Fehler bei {symbol}: {e}")
        return None

# --- KI ENTSCHEIDUNG (EINSTIEG) ---
def get_entry_decision(market_data):
    router = ModelRouter()
    rsi_5m = calculate_rsi(market_data['closes_5m'])
    rsi_15m = calculate_rsi(market_data['closes_15m'])
    
    prompt = f"""
    Ich bin ein flexibler Trader. Der aktuelle Kurs von {market_data['symbol']} ist {market_data['last']}.
    Mein 5-Minuten-RSI liegt bei {rsi_5m:.1f}, mein 15-Minuten-RSI bei {rsi_15m:.1f}.
    
    Aufgabe: Entscheide, ob ich jetzt EINSTEIGEN (BUY/SELL) oder WARTEN (HOLD) soll.
    Berücksichtige, dass ich schnell wieder aussteige, wenn der Trend kippt (Scalping).
    Antworte im JSON-Format:
    {{
        "decision": "BUY" oder "SELL" oder "HOLD",
        "reasoning": "Kurze Begründung",
        "stop_loss": 0.0,
        "take_profit": 0.0
    }}
    """
    answer, _ = router.route(prompt, system_context="Du antwortest NUR mit JSON.", preferred_model="groq")
    match = re.search(r'\{.*\}', answer, re.DOTALL)
    if match:
        try: return json.loads(match.group(0))
        except: pass
    return {"decision": "HOLD", "reasoning": "Fehler", "stop_loss": 0.0, "take_profit": 0.0}

# --- HAUPTLOOP ---
def main_loop():
    print("🧠 KI-Trader gestartet (flexibles Scalping-Modus). 24/7 aktiv.", flush=True)
    from agents.gemini_agent import GeminiCoreAgent
    agent = GeminiCoreAgent()
    last_chat_id = 0

    while True:
        try:
            for symbol in MONITORED_ASSETS:
                # 1. Daten abrufen (nur für 5m/15m, um exit schnell zu checken)
                data = get_asset_data(symbol)
                if not data: continue
                
                # 2. Checken: Halten wir das Asset bereits? (Aktiven Trade in DB suchen)
                active_trades = requests.get(
                    f"{SUPABASE_URL}/rest/v1/Handelsgeschichte?select=id,Eintrittspreis&Vermögenswert=eq.{symbol}&Status=eq.ACTIVE",
                    headers=HEADERS
                ).json()
                
                has_position = len(active_trades) > 0
                entry_price = float(active_trades[0]['Eintrittspreis']) if has_position else 0.0
                trade_id = active_trades[0]['id'] if has_position else 0
                
                rsi_5m = calculate_rsi(data['closes_5m'])
                rsi_15m = calculate_rsi(data['closes_15m'])
                
                # 3. EXIT-LOGIK (Falls wir eine Position halten und der 5min RSI > 70 (überkauft) ist)
                if has_position:
                    if rsi_5m > 70 or rsi_15m > 70:
                        # Schneller Ausstieg ohne KI (wie ein menschlicher Trader, der den Bildschirm sieht)
                        pnl = data['last'] - entry_price
                        close_trade(symbol, data['last'], pnl)
                        send_chat_message("system", f"⚡ {symbol}: Schneller Exit! RSI bei {rsi_5m:.1f}. Gewinn: ${pnl:.2f}")
                        print(f"⚡ {symbol} sofort ausgestiegen (RSI {rsi_5m:.1f}). PnL: {pnl:.2f}", flush=True)
                        continue
                    else:
                        # Wir halten noch, aber sagen dem Bot, wie es läuft (nur für das Log)
                        print(f"📈 Halte {symbol} noch. RSI: {rsi_5m:.1f}", flush=True)
                
                # 4. ENTRY-LOGIK (Falls wir KEINE Position halten)
                elif not has_position:
                    # Entscheidung via KI einholen
                    decision = get_entry_decision(data)
                    if decision['decision'] in ['BUY', 'SELL']:
                        # Trade eröffnen
                        save_trade(
                            asset=symbol,
                            direction=decision['decision'],
                            entry_price=data['last'],
                            stop_loss=decision.get('stop_loss', 0.0),
                            take_profit=decision.get('take_profit', 0.0),
                            reasoning=decision.get('reasoning', ''),
                            indicators=f"5m RSI: {rsi_5m:.1f}, 15m RSI: {rsi_15m:.1f}",
                            expected_move='Scalping',
                            status='ACTIVE'  # WICHTIG: Jetzt auf ACTIVE setzen!
                        )
                        send_chat_message("system", f"🟢 Einstieg {symbol}: {decision['decision']} bei {data['last']}. Grund: {decision['reasoning']}")
                        print(f"🟢 {symbol} eröffnet: {decision['decision']}", flush=True)

            # Chat nebenbei bearbeiten
            if int(time.time()) % 5 == 0:
                new_id = agent.process_live_chat(last_chat_id)
                if new_id is not None:
                    last_chat_id = new_id

            time.sleep(2) # Alle 2 Sekunden durch alle Assets loopen (flexibel)
        except Exception as e:
            print(f"❌ Fehler im Hauptloop: {e}", flush=True)
            time.sleep(10)

if __name__ == "__main__":
    main_loop()
